use rocket::Config;
use std::net::{SocketAddr, ToSocketAddrs};
use std::path::{PathBuf, Path};

pub struct MoMMIConfig {
    commloop_address: SocketAddr,
    commloop_password: String,
    repo_path: PathBuf,
    /// Seconds.
    changelog_delay: f32,
    github_key: String,
}

impl MoMMIConfig {
    pub fn new(config: &Config) -> MoMMIConfig {
        MoMMIConfig {
            commloop_address: config
                .get_str("commloop-address")
                .unwrap_or("127.0.0.1:1679")
                .to_socket_addrs()
                .unwrap()
                .next()
                .unwrap(),
            commloop_password: config
                .get_str("commloop-password")
                .expect("Must set commloop password for MoMMI.")
                .to_owned(),
            repo_path: config
                .get_str("repo-path")
                .expect("Must set repo path.")
                .into(),
            changelog_delay: config
                .get_float("changelog-delay")
                .map(|f| f as f32)
                .unwrap_or(30.0),
            github_key: config
                .get_str("github-key")
                .expect("Must set github key.")
                .to_owned(),
        }
    }

    pub fn get_commloop_address(&self) -> &SocketAddr {
        &self.commloop_address
    }

    pub fn get_commloop_password(&self) -> &str {
        &self.commloop_password
    }

    pub fn get_repo_path(&self) -> &Path {
        &self.repo_path
    }

    pub fn get_changelog_delay(&self) -> f32 {
        self.changelog_delay
    }

    pub fn get_github_key(&self) -> &str {
        &self.github_key
    }
}
