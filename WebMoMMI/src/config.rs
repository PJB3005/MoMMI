use rocket::{Config};
use rocket::config::ConfigError;

pub struct MoMMIConfig {
    /// Address, Password
    commloop: Option<(String, String)>,
    github_key: String,
}

impl MoMMIConfig {
    pub fn new(config: &Config) -> Result<MoMMIConfig, String> {
        let commloop_address = match config.get_str("commloop-address") {
            Ok(x) => Some(x.to_owned()),
            Err(ConfigError::UnknownKey(_)) | Err(ConfigError::NotFound) => None,
            Err(x) => return Err(format!("Unable to fetch commloop address config: {}", x)),
        };
        let commloop_password = match config.get_str("commloop-password") {
            Ok(x) => Some(x.to_owned()),
            Err(ConfigError::UnknownKey(_)) | Err(ConfigError::NotFound) => None,
            Err(x) => return Err(format!("Unable to fetch commloop password config: {}", x)),
        };

        let commloop = match (commloop_address, commloop_password) {
            (Some(addr), Some(pass)) => Some((addr, pass)),
            (None, None) => None,
            _ => return Err("commloop-address and commloop-password must either both or neither be set.".to_owned())
        };

        Ok(MoMMIConfig {
            commloop: commloop,
            github_key: config
                .get_str("github-key")
                .expect("Must set github key.")
                .to_owned(),
        })
    }

    // Order of the tuple is address, password.
    pub fn get_commloop<'a>(&'a self) -> Option<(&'a str, &'a str)> {
        match self.commloop {
            None => None,
            Some((ref addr, ref pass)) => Some((addr.as_str(), pass.as_str()))
        }
    }

    pub fn has_commloop(&self) -> bool {
        self.commloop.is_some()
    }

    pub fn get_github_key(&self) -> &str {
        &self.github_key
    }
}
