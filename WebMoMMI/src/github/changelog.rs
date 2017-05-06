use std::sync::{Mutex, MutexGuard};
use std::thread;
use std::time::{Instant, Duration};
use std::collections::HashMap;
use rocket::config;


lazy_static! {
    pub static ref CHANGELOG_MANAGER: Mutex<ChangelogManager> = {
        Mutex::new(ChangelogManager {pending: Vec::new(), last_time: None})
    };
}

pub struct ChangelogManager {
    pending: Vec<Changelog>,
    // If None, no thread is currently on it.
    last_time: Option<Instant>
}

/// Represents a new changelog entry.
#[derive(Debug, Clone)]
pub struct Changelog {
    author: String,
    additions: Vec<(ChangelogEntryType, String)>
}

#[derive(Debug, Copy, Clone, Hash, Eq, PartialEq)]
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
    Tgs
}

pub fn add_changelog(changelogs: &[Changelog]) {
    let mut lock = CHANGELOG_MANAGER.lock().unwrap();
    let should_spawn_thread = lock.last_time.is_none();
    lock.pending.extend_from_slice(changelogs);
    lock.last_time = Some(Instant::now());

    if should_spawn_thread {
        // Nobody currently processing.
        lock.last_time = Some(Instant::now());
        thread::Builder::new()
            .name("Changelog thread".into())
            .spawn(|| {
                handle_changelog_thread();
            }).unwrap();
    }
}

fn handle_changelog_thread() {
    let config = config::active().unwrap();
    let delay = config.extras.get("changelog-delay").and_then(|x| x.as_integer()).unwrap_or(5) as u64;

    loop {
        let time = {
            let lock = CHANGELOG_MANAGER.lock().unwrap();
            let elapsed = lock.last_time.as_ref().unwrap().elapsed();
            if elapsed.as_secs() > delay {
                return do_changelog(lock);
            }

            match Duration::from_secs(delay).checked_sub(elapsed) {
                Some(t) => t,
                None => return do_changelog(lock)
            }
        };
        thread::sleep(time);
    }
}

// Pass the lock directly so we don't risk race conditions.
fn do_changelog(mut lock: MutexGuard<ChangelogManager>) {
    // Get what we need and drop the lock.
    // so we don't hang everything for the time it takes for the git commands and stuff.
    let changelogs = lock.pending.clone();
    lock.pending.truncate(0);
    lock.last_time = None;
    drop(lock);

    

}
