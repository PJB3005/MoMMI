//! Handles GitHub changelog generation and MoMMI GitHub relaying.

use crate::config::MoMMIConfig;
use crate::mommi::commloop;
use crypto::hmac::Hmac;
use crypto::mac::{Mac, MacResult};
use crypto::sha1::Sha1;
use rocket::data::Data;
use rocket::http::{RawStr, Status};
use rocket::request::{FromRequest, Request};
use rocket::{request, Outcome, State};
use rustc_serialize::hex::FromHex;
use serde_json::json;
use serde_json::Value;
use std::io::Read;

pub mod changelog;
pub mod data;

use self::data::*;
use crate::github::changelog::try_handle_changelog;

#[allow(dead_code)]
pub struct GitHubData {
    event: String,
    signature: String,
    delivery: String,
}

#[allow(dead_code)]
impl GitHubData {
    pub fn get_event(&self) -> &str {
        &self.event
    }

    pub fn get_signature(&self) -> &str {
        &self.signature
    }

    pub fn verify_signature(&self, data: Data, config: &MoMMIConfig) -> Result<Value, Status> {
        let mut buffer = Vec::new();
        data.open()
            .read_to_end(&mut buffer)
            .map_err(|_| Status::InternalServerError)?;
        let password = config
            .get_github_key()
            .expect("GitHub key config should be set!");
        let mut hmac = Hmac::new(Sha1::new(), password.as_bytes());
        hmac.input(&buffer);
        let result = hmac.result();

        let signature = match self.get_signature().from_hex() {
            Ok(bytes) => bytes,
            Err(x) => {
                println!("{:?}", x);
                return Err(Status::BadRequest);
            }
        };

        if result != MacResult::new(&signature) {
            return Err(Status::Forbidden);
        }

        // ALRIGHT. VALIDATED.
        // Now we can parse the JSON and return it.
        match serde_json::from_slice::<Value>(&buffer) {
            Ok(x) => Ok(x),
            Err(_) => Err(Status::BadRequest),
        }
    }

    pub fn get_delivery(&self) -> &str {
        &self.delivery
    }
}

impl<'a, 'r> FromRequest<'a, 'r> for GitHubData {
    type Error = ();
    fn from_request(request: &'a Request<'r>) -> request::Outcome<GitHubData, ()> {
        let event = match request.headers().get_one("X-GitHub-Event") {
            Some(t) => t.to_owned(),
            _ => return Outcome::Failure((Status::BadRequest, ())),
        };

        // This is both the most beautiful and ugly section of code I have written yet.
        let signature = match request
            .headers()
            .get_one("X-Hub-Signature")
            .map(|x| x.split('='))
            .map(|mut x| (x.next(), x.next()))
        {
            Some((Some("sha1"), Some(hex))) => hex.to_owned(),
            Some((Some(_), Some(_))) => return Outcome::Failure((Status::NotImplemented, ())),
            _ => return Outcome::Failure((Status::BadRequest, ())),
        };

        let delivery = match request.headers().get_one("X-GitHub-Delivery") {
            Some(t) => t.to_owned(),
            _ => return Outcome::Failure((Status::BadRequest, ())),
        };

        Outcome::Success(GitHubData {
            event,
            signature,
            delivery,
        })
    }
}

#[post("/dev/git_hooks/webmommi", data = "<body>")]
pub fn post_github_alt(
    github: GitHubData,
    body: Data,
    config: State<MoMMIConfig>,
) -> Result<String, Status> {
    post_github(github, body, config)
}

#[post("/mommi/github", data = "<body>")]
pub fn post_github_new(
    github: GitHubData,
    body: Data,
    config: State<MoMMIConfig>,
) -> Result<String, Status> {
    post_github(github, body, config)
}

#[allow(unused_variables)]
#[post("/mommi/github/<id>", data = "<body>")]
pub fn post_github_new_specific(
    github: GitHubData,
    body: Data,
    config: State<MoMMIConfig>,
    id: &RawStr,
) -> Result<String, Status> {
    post_github(github, body, config)
}

// `/changelog` due to legacy reasons.
#[post("/changelog", data = "<body>")]
pub fn post_github(
    github: GitHubData,
    body: Data,
    config: State<MoMMIConfig>,
) -> Result<String, Status> {
    let data = github.verify_signature(body, &config)?;
    let event = github.get_event();
    match event {
        "ping" => return Ok("pong".into()),
        "pull_request" => event_pull_request(
            &serde_json::from_value(data.clone()).map_err(|_| Status::BadRequest)?,
            &config,
        ),
        _ => {}
    };

    if !config.has_commloop() {
        return Ok("Worked!".into());
    }

    let (addr, pass) = config.get_commloop().unwrap();

    // Code for relaying each event to MoMMI.
    let meta = data
        .pointer("/repository/full_name")
        .and_then(|x| x.as_str())
        .unwrap_or("");

    let json = json!({
        "event": event,
        "data": data
    });

    commloop(addr, pass, "github_event", meta, &json).map_err(|_| Status::InternalServerError)?;

    Ok("Worked!".into())
}

fn event_pull_request(event: &PullRequestEvent, config: &MoMMIConfig) {
    try_handle_changelog(event, config);
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_github_auth() {
        use crate::config::MoMMIConfig;
        use crypto::hmac::Hmac;
        use crypto::mac::Mac;
        use crypto::sha1::Sha1;
        use rocket;
        use rocket::config::{Config, Environment};
        use rocket::http::{ContentType, Header, Status};
        use rocket::local::Client;
        use rustc_serialize::hex::ToHex;
        use serde_json::json;

        const GITHUB_KEY: &'static str = "foobar";

        let config = Config::build(Environment::Development)
            .workers(1)
            .extra("github-key", GITHUB_KEY)
            .unwrap();

        let mut rocket =
            rocket::custom(config).mount("/", routes![super::post_github, super::post_github_alt]);

        let config = MoMMIConfig::new(rocket.config()).unwrap();
        rocket = rocket.manage(config);

        let json = serde_json::to_string(&json!({
            "zen": "Non-blocking is better than blocking."
        }))
        .unwrap();

        let client = Client::new(rocket).unwrap();

        let mut hmac = Hmac::new(Sha1::new(), GITHUB_KEY.as_bytes());
        hmac.input(json.as_bytes());
        let result = hmac.result().code().to_hex();

        for request_url in ["/changelog", "/dev/git_hooks/webmommi"].iter().map(|x| *x) {
            let mut request = client.post(request_url).body(&json);
            request.add_header(ContentType::JSON);
            request.add_header(Header::new("X-GitHub-Event", "ping"));
            request.add_header(Header::new("X-GitHub-Delivery", "0000"));
            request.add_header(Header::new("X-Hub-Signature", format!("sha1={}", result)));
            let mut response = request.dispatch();
            assert_eq!(response.status(), Status::Ok);
            assert_eq!(
                response.body().and_then(|f| f.into_string()),
                Some("pong".into())
            );

            let mut request = client.post(request_url).body(&json);
            request.add_header(ContentType::JSON);
            request.add_header(Header::new("X-GitHub-Event", "ping"));
            request.add_header(Header::new("X-GitHub-Delivery", "0000"));
            request.add_header(Header::new("X-Hub-Signature", format!("sha2={}", result)));
            assert_eq!(request.dispatch().status(), Status::NotImplemented);

            let mut request = client.post(request_url).body(&json);
            request.add_header(ContentType::JSON);
            request.add_header(Header::new("X-GitHub-Event", "ping"));
            request.add_header(Header::new("X-GitHub-Delivery", "0000"));
            request.add_header(Header::new(
                "X-Hub-Signature",
                "sha1=0000000000000000000000000000000000000000",
            ));
            assert_eq!(request.dispatch().status(), Status::Forbidden);

            let mut request = client.post(request_url).body(&json);
            request.add_header(ContentType::JSON);
            request.add_header(Header::new("X-GitHub-Event", "ping"));
            request.add_header(Header::new("X-GitHub-Delivery", "0000"));
            request.add_header(Header::new("X-Hub-Signature", "sha1=00000"));
            assert_eq!(request.dispatch().status(), Status::BadRequest);

            let mut request = client.post(request_url).body(&json);
            request.add_header(ContentType::JSON);
            assert_eq!(request.dispatch().status(), Status::BadRequest);
        }
    }
}
