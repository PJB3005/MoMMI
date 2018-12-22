use crate::config::MoMMIConfig;
use crate::github::data::{PullRequestAction, PullRequestEvent};
use lazy_static::lazy_static;
use regex::{Regex, RegexBuilder};
use rocket::Config;
use serde::de::{Error, MapAccess, Visitor};
use serde::ser::SerializeMap;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::fmt;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use std::sync::{Mutex, MutexGuard};
use std::thread;
use std::time::{Duration, Instant};

pub fn try_handle_changelog(event: &PullRequestEvent, config: &MoMMIConfig) {
    if event.action != PullRequestAction::Closed
        || !event.pull_request.merged
        || !config.has_changelog_repo_path()
    {
        // Not a merge
        return;
    }

    let additions = parse_body_changelog(&event.pull_request.body);

    if additions.len() == 0 {
        return;
    }

    let changelog = Changelog {
        author: "placeholder".into(),
        additions,
        delete_after: true,
    };

    let mut changelog_path = config.get_changelog_repo_path().unwrap().to_path_buf();
    changelog_path.push("html/changelogs");
    changelog_path.push(&format!("PR-{}-temp.yml", event.number));

    match write_temp_changelog(&changelog_path, changelog) {
        Err(e) => eprintln!("Error writing changelog temp file: {:?}", e),
        _ => {}
    };

    process_changelogs();
}

fn parse_body_changelog(body: &str) -> Vec<ChangelogEntry> {
    lazy_static! {
        static ref header_re: Regex = RegexBuilder::new(r#"(?::cl:|🆑) *\r?\n(.+)$"#).dot_matches_new_line(true).build().unwrap();
        static ref entry_re: Regex = RegexBuilder::new(r#"^ *[*-]? *(bugfix|wip|tweak|soundadd|sounddel|rscdel|rscadd|imageadd|imagedel|spellcheck|experiment|tgs): *(\S[^\n\r]+)$"#).multi_line(true).build().unwrap();
    }

    let content = match header_re.captures(body) {
        Some(capture) => capture.get(1).unwrap().as_str(),
        _ => return Vec::new(),
    };

    entry_re
        .captures_iter(content)
        .map(|m| {
            let entry_type = match m.get(1).unwrap().as_str() {
                "bugfix" => ChangelogEntryType::Bugfix,
                "wip" => ChangelogEntryType::Wip,
                "tweak" => ChangelogEntryType::Tweak,
                "soundadd" => ChangelogEntryType::Soundadd,
                "sounddel" => ChangelogEntryType::Sounddel,
                "rscdel" => ChangelogEntryType::Rscdel,
                "rscadd" => ChangelogEntryType::Rscadd,
                "imageadd" => ChangelogEntryType::Imageadd,
                "imagedel" => ChangelogEntryType::Imagedel,
                "spellcheck" => ChangelogEntryType::Spellcheck,
                "experiment" => ChangelogEntryType::Experiment,
                "tgs" => ChangelogEntryType::Tgs,
                _ => unreachable!(),
            };

            ChangelogEntry(entry_type, m.get(2).unwrap().as_str().to_owned())
        })
        .collect()
}

fn write_temp_changelog(path: &Path, changelog: Changelog) -> std::io::Result<()> {
    let mut file = File::create(path)?;
    serde_yaml::to_writer(&file, &changelog).unwrap(); // TODO: Remove unwrap.
    file.flush()?;
    Ok(())
}

lazy_static! {
    pub static ref CHANGELOG_MANAGER: Mutex<ChangelogManager> =
        { Mutex::new(ChangelogManager { last_time: None }) };
}

pub struct ChangelogManager {
    // If None, no thread is currently on it.
    last_time: Option<Instant>,
}

/// Represents a new changelog entry.
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "kebab-case")]
pub struct Changelog {
    pub author: String,
    pub additions: Vec<ChangelogEntry>,
    pub delete_after: bool,
}

#[derive(Debug, Clone)]
pub struct ChangelogEntry(ChangelogEntryType, String);

impl Serialize for ChangelogEntry {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let mut map = serializer.serialize_map(Some(1))?;
        map.serialize_entry(&self.0, &self.1)?;
        map.end()
    }
}

impl<'de> Deserialize<'de> for ChangelogEntry {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_map(ChangelogEntryVisitor)
    }
}

struct ChangelogEntryVisitor;

impl<'de> Visitor<'de> for ChangelogEntryVisitor {
    type Value = ChangelogEntry;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("A single-element map")
    }

    fn visit_map<M>(self, mut access: M) -> Result<Self::Value, M::Error>
    where
        M: MapAccess<'de>,
    {
        match access.next_entry()? {
            Some((key, value)) => {
                let value = ChangelogEntry(key, value);
                match access.next_key::<ChangelogEntryType>()? {
                    Some(_) => Err(M::Error::invalid_length(2, &"A single-element map.")),
                    _ => Ok(value),
                }
            }
            None => Err(M::Error::invalid_length(0, &"A single-element map.")),
        }
    }
}

#[derive(Debug, Copy, Clone, Hash, Eq, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ChangelogEntryType {
    Bugfix,
    Wip,
    Tweak,
    Soundadd,
    Sounddel,
    Rscadd,
    Rscdel,
    Imageadd,
    Imagedel,
    Spellcheck,
    Experiment,
    Tgs,
}

pub fn process_changelogs() {
    let mut lock = CHANGELOG_MANAGER.lock().unwrap();
    let should_spawn_thread = lock.last_time.is_none();
    lock.last_time = Some(Instant::now());

    if should_spawn_thread {
        // Nobody currently processing.
        lock.last_time = Some(Instant::now());
        thread::Builder::new()
            .name("Changelog thread".into())
            .spawn(|| {
                handle_changelog_thread();
            })
            .unwrap();
    }
}

fn handle_changelog_thread() {
    let config = Config::active().unwrap();
    let delay = config
        .extras
        .get("changelog-delay")
        .and_then(|x| x.as_integer())
        .unwrap_or(5) as u64;

    loop {
        let time = {
            let lock = CHANGELOG_MANAGER.lock().unwrap();
            let elapsed = lock.last_time.as_ref().unwrap().elapsed();
            if elapsed.as_secs() > delay {
                return do_changelog(lock);
            }

            match Duration::from_secs(delay).checked_sub(elapsed) {
                Some(t) => t,
                None => return do_changelog(lock),
            }
        };
        thread::sleep(time);
    }
}

// Pass the lock directly so we don't risk race conditions.
fn do_changelog(mut lock: MutexGuard<ChangelogManager>) {
    // Get what we need and drop the lock.
    // so we don't hang everything for the time it takes for the git commands and stuff.
    //let changelogs = lock.pending.clone();
    //lock.pending.truncate(0);
    lock.last_time = None;
    drop(lock);
}
