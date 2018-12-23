use crate::config::MoMMIConfig;
use crate::github::data::{PullRequestAction, PullRequestEvent, PushEvent};
use crate::mommi::commloop;
use lazy_static::lazy_static;
use regex::{Regex, RegexBuilder};
use serde::de::{Error, MapAccess, Visitor};
use serde::ser::SerializeMap;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::fmt;
use std::fs::{read_dir, File};
use std::io::Write;
use std::path::Path;
use std::process::Command;
use std::sync::Arc;
use std::sync::{Mutex, MutexGuard};
use std::thread;
use std::time::{Duration, Instant};

pub fn try_handle_changelog_pr(event: &PullRequestEvent, config: &Arc<MoMMIConfig>) {
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
        author: event.pull_request.user.login.clone(),
        changes: additions,
        delete_after: Some(true),
    };

    let mut changelog_path = config.get_changelog_repo_path().unwrap().to_path_buf();
    changelog_path.push(&format!("html/changelogs/PR-{}-temp.yml", event.number));

    match write_temp_changelog(&changelog_path, changelog) {
        Err(e) => eprintln!("Error writing changelog temp file: {:?}", e),
        _ => {}
    };

    process_changelogs(config);
}

pub fn try_handle_changelog_push(event: &PushEvent, config: &Arc<MoMMIConfig>) {
    lazy_static! {
        static ref is_changelog_re: Regex = Regex::new(r#"^html/changelogs/[^.].*\.yml$"#).unwrap();
    }

    for filename in event.commits.iter().flat_map(|c| c.added.iter().chain(c.modified.iter())) {
        println!("{}", filename);
        if is_changelog_re.is_match(filename) {
            process_changelogs(config);
            return
        }
    }
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
    pub changes: Vec<ChangelogEntry>,
    pub delete_after: Option<bool>,
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

pub fn process_changelogs(config: &Arc<MoMMIConfig>) {
    let mut lock = CHANGELOG_MANAGER.lock().unwrap();
    let should_spawn_thread = lock.last_time.is_none();
    lock.last_time = Some(Instant::now());

    if should_spawn_thread {
        // Nobody currently processing.
        lock.last_time = Some(Instant::now());
        let config = config.clone();
        thread::Builder::new()
            .name("Changelog thread".into())
            .spawn(move || {
                handle_changelog_thread(config);
            })
            .unwrap();
    }
}

fn handle_changelog_thread(config: Arc<MoMMIConfig>) {
    let delay = config.get_changelog_delay();

    loop {
        let time = {
            let lock = CHANGELOG_MANAGER.lock().unwrap();
            let elapsed = lock.last_time.as_ref().unwrap().elapsed();
            if elapsed.as_secs() > delay {
                return do_changelog(lock, config);
            }

            match Duration::from_secs(delay).checked_sub(elapsed) {
                Some(t) => t,
                None => return do_changelog(lock, config),
            }
        };
        thread::sleep(time);
    }
}

// Pass the lock directly so we don't risk race conditions.
fn do_changelog(mut lock: MutexGuard<ChangelogManager>, config: Arc<MoMMIConfig>) {
    println!("Running changelogs!");
    // Get what we need and drop the lock.
    // so we don't hang everything for the time it takes for the git commands and stuff.
    lock.last_time = None;
    drop(lock);

    let path = config.get_changelog_repo_path().unwrap();
    let ssh_config = config
        .get_ssh_key()
        .map(|p| format!("ssh -i {}", p.to_string_lossy()));

    // Git pull the repo.
    let mut command = Command::new("git");
    command
        .arg("pull")
        .arg("origin")
        .arg("--ff-only")
        .current_dir(&path);
    if let Some(ref ssh_command) = ssh_config {
        command.env("GIT_SSH_COMMAND", &ssh_command);
    }
    let status = command.status().unwrap();

    assert!(status.success());

    let mut changelog_dir_path = path.to_owned();
    changelog_dir_path.push("html/changelogs");

    // Send changelog files over to MoMMI maybe.
    if let Some((addr, pass)) = config.get_commloop() {
        for entry in read_dir(&changelog_dir_path).unwrap() {
            let entry = entry.unwrap();
            let os_file_name = entry.file_name();
            let file_name = os_file_name.to_str().unwrap();
            if file_name.starts_with(".")
                || !file_name.ends_with(".yml")
                || file_name == "example.yml"
            {
                continue;
            }

            println!("{}", file_name);

            let file = File::open(entry.path()).unwrap();
            let data: Changelog = serde_yaml::from_reader(&file).unwrap();

            if data.changes.len() == 0 {
                continue;
            }

            commloop(addr, pass, "changelog", "", data).unwrap();
        }
    }

    // Run changelog script.
    let status = Command::new("python2")
        .arg("tools/changelog/ss13_genchangelog.py")
        .arg("html/changelog.html")
        .arg("html/changelogs")
        .current_dir(&path)
        .status()
        .unwrap();

    assert!(status.success());

    Command::new("git")
        .arg("update-index")
        .arg("--refresh")
        .current_dir(&path)
        .status()
        .unwrap();

    // See if repo is dirty.
    let status = Command::new("git")
        .arg("diff-index")
        .arg("--exit-code")
        .arg("HEAD")
        .current_dir(&path)
        .status()
        .unwrap();

    if status.code().unwrap_or(0) == 0 {
        // No changes, nothing to commit.
        return;
    }

    let status = Command::new("git")
        .arg("add")
        .arg(".")
        .arg("-A")
        .current_dir(&path)
        .status()
        .unwrap();

    assert!(status.success());

    let status = Command::new("git")
        .arg("commit")
        .arg("-m")
        .arg("[ci skip] Automatic changelog update.")
        .current_dir(&path)
        .status()
        .unwrap();

    assert!(status.success());

    // Git push the repo.
    let mut command = Command::new("git");
    command.arg("push").arg("origin").current_dir(&path);
    if let Some(ref ssh_command) = ssh_config {
        command.env("GIT_SSH_COMMAND", &ssh_command);
    }
    let status = command.status().unwrap();

    assert!(status.success());

    println!("done");
}
