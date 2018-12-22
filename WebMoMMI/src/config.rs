use rocket::config::ConfigError;
use rocket::Config;
use std::path::{Path, PathBuf};



#[derive(Debug)]
pub struct MoMMIConfig {
    /// Address, Password
    commloop: Option<(String, String)>,
    github_key: Option<String>,
    changelog_repo_path: Option<PathBuf>,
    verify_github: bool,
    changelog_delay: u64,
    ssh_key: Option<PathBuf>,
}

impl MoMMIConfig {
    pub fn new(config: &Config) -> Result<MoMMIConfig, String> {
        println!("{:?}", config.extras);
        let commloop_address = match config.get_str("commloop-address") {
            Ok(x) => Some(x.to_owned()),
            Err(ConfigError::Missing(_)) => None,
            Err(x) => return Err(format!("Unable to fetch commloop address config: {}", x)),
        };
        let commloop_password = match config.get_str("commloop-password") {
            Ok(x) => Some(x.to_owned()),
            Err(ConfigError::Missing(_)) => None,
            Err(x) => return Err(format!("Unable to fetch commloop password config: {}", x)),
        };

        let commloop =
            match (commloop_address, commloop_password) {
                (Some(addr), Some(pass)) => Some((addr, pass)),
                (None, None) => None,
                _ => return Err(
                    "commloop-address and commloop-password must either both or neither be set."
                        .to_owned(),
                ),
            };

        let github_key = match config.get_str("github-key") {
            Ok(x) => Some(x.to_owned()),
            Err(ConfigError::Missing(_)) => None,
            Err(x) => return Err(format!("Unable to fetch github key config: {}", x)),
        };

        let changelog_repo_path = match config.get_str("changelog-repo-path") {
            Ok(x) => Some(x.into()),
            Err(ConfigError::Missing(_)) => None,
            Err(x) => return Err(format!("Unable to fetch changelog repo path config: {}", x)),
        };

        let verify_github = match config.get_bool("verify-github") {
            Ok(x) => x,
            Err(ConfigError::Missing(_)) => true,
            Err(x) => return Err(format!("Unable to fetch verify_github config: {}", x)),
        };

        let ssh_key = match config.get_str("ssh-key") {
            Ok(x) => Some(x.into()),
            Err(ConfigError::Missing(_)) => None,
            Err(x) => return Err(format!("Unable to fetch ssh key config: {}", x)),
        };

        let changelog_delay = match config.get_int("changelog-delay") {
            Ok(x) => x as u64,
            Err(ConfigError::Missing(_)) => 5,
            Err(x) => return Err(format!("Unable to fetch ssh key config: {}", x)),
        };

        Ok(MoMMIConfig {
            commloop,
            github_key,
            changelog_repo_path,
            verify_github,
            ssh_key,
            changelog_delay,
        })
    }

    // Order of the tuple is address, password.
    pub fn get_commloop(&self) -> Option<(&str, &str)> {
        match self.commloop {
            None => None,
            Some((ref addr, ref pass)) => Some((addr.as_str(), pass.as_str())),
        }
    }

    pub fn has_commloop(&self) -> bool {
        self.commloop.is_some()
    }

    pub fn has_github_key(&self) -> bool {
        self.github_key.is_some()
    }

    pub fn get_github_key(&self) -> Option<&str> {
        self.github_key.as_ref().map(String::as_ref)
    }

    pub fn has_changelog_repo_path(&self) -> bool {
        self.changelog_repo_path.is_some()
    }

    pub fn get_changelog_repo_path(&self) -> Option<&Path> {
        self.changelog_repo_path.as_ref().map(|p| &**p)
    }

    pub fn verify_github(&self) -> bool {
        self.verify_github
    }

    pub fn get_changelog_delay(&self) -> u64 { self.changelog_delay }

    pub fn get_ssh_key(&self) -> Option<&Path> { self.ssh_key.as_ref().map(|p| &**p) }
}
