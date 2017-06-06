//! Handles GitHub changelog generation and MoMMI GitHub relaying.

// use rocket_contrib::{JSON, Value}
use super::mommi::commloop;
use rocket::data::Data;
use rocket::{request, Outcome};
use rocket::request::{FromRequest, Request};
use rocket::http::Status;
use rocket::response::Failure;
use serde_json::Value;
use serde_json;
use crypto::sha1::Sha1;
use crypto::hmac::Hmac;
use crypto::mac::{Mac, MacResult};
use rustc_serialize::hex::FromHex;
use rocket::config;
use std::io::Read;

pub mod changelog;

#[allow(dead_code)]
pub struct GitHubData {
    event: String,
    signature: String,
    delivery: String
}

#[allow(dead_code)]
impl GitHubData {
    pub fn get_event(&self) -> &str {
        &self.event
    }

    pub fn get_signature(&self) -> &str {
        &self.signature
    }

    pub fn verify_signature(&self, data: Data) -> Result<Value, Failure> {
        let mut buffer = Vec::new();
        data.open().read_to_end(&mut buffer).map_err(|_| Failure(Status::InternalServerError))?;
        let password = config::active().unwrap().extras.get("github-key").and_then(|x| x.as_str()).unwrap_or("foobar");
        let mut hmac = Hmac::new(Sha1::new(), password.as_bytes());
        hmac.input(&buffer);
        let result = hmac.result();

        let signature = match self.get_signature().from_hex() {
            Ok(bytes) => bytes,
            Err(x) => {
                println!("{:?}", x);
                return Err(Failure(Status::BadRequest))
            }
        };

        if result != MacResult::new(&signature) {
            return Err(Failure(Status::Forbidden));
        }

        // ALRIGHT. VALIDATED.
        // Now we can parse the JSON and return it.
        match serde_json::from_slice::<Value>(&buffer) {
            Ok(x) => Ok(x),
            Err(_) => Err(Failure(Status::BadRequest))
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
            _ => return Outcome::Failure((Status::BadRequest, ()))
        };

        // This is both the most beautiful and ugly section of code I have written yet.
        let signature = match request.headers().get_one("X-Hub-Signature")
            .map(|x| x.split('=')).map(|mut x| (x.next(), x.next())) {
            Some((Some("sha1"), Some(hex))) => hex.to_owned(),
            Some((Some(_), Some(_))) => return Outcome::Failure((Status::NotImplemented, ())),
            _ => return Outcome::Failure((Status::BadRequest, ()))
        };

        let delivery = match request.headers().get_one("X-GitHub-Delivery") {
            Some(t) => t.to_owned(),
            _ => return Outcome::Failure((Status::BadRequest, ()))
        };

        Outcome::Success(GitHubData {event: event, signature: signature, delivery: delivery})
    }
}

// `/changelog` due to legacy reasons.
#[allow(unmounted_route)]
#[post("/changelog", data = "<body>")]
pub fn post_github(github: GitHubData, body: Data) -> Result<String, Failure> {
    let data = github.verify_signature(body)?;
    let event = github.get_event();
    match event {
        "ping" => return Ok("pong".into()),
        //"pull_request" => {},
        _ => {}
    };


    // Code for relaying each event to MoMMI.
    let config = config::active().unwrap();
    let address = config.extras.get("commloop-address").and_then(|x| x.as_str()).unwrap_or("127.0.0.1:1680");
    let password = config.extras.get("commloop-password").and_then(|x| x.as_str()).unwrap_or("foobar");
    let meta = data.pointer("/repository/full_name").and_then(|x| x.as_str()).unwrap_or("");

    let json = json!({
        "event": event,
        "data": data
    });

    commloop(address, password, "github_event", meta, &json).map_err(|_| Failure(Status::InternalServerError))?;

    Ok("Worked!".into())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_github_auth() {
        use rocket;
        use rocket::config::{Config, Environment};
        use rocket::testing::MockRequest;
        use rocket::http::Method::*;
        use rocket::http::{Header, ContentType, Status};
        use crypto::sha1::Sha1;
        use crypto::hmac::Hmac;
        use crypto::mac::Mac;
        use rustc_serialize::hex::ToHex;
        use serde_json;

        const GITHUB_KEY: &'static str = "foobar";

        let config = Config::build(Environment::Development)
            .workers(1)
            .extra("github-key", GITHUB_KEY)
            .unwrap();

        let rocket = rocket::custom(config, false)
            .mount("/", routes![super::post_github]);

        let json = serde_json::to_string(&json!({
            "zen": "Non-blocking is better than blocking."
        })).unwrap();

        let mut hmac = Hmac::new(Sha1::new(), GITHUB_KEY.as_bytes());
        hmac.input(json.as_bytes());
        let result = hmac.result().code().to_hex();

        let mut request = MockRequest::new(Post, "/changelog").body(&json);
        request.add_header(ContentType::JSON);
        request.add_header(Header::new("X-GitHub-Event", "ping"));
        request.add_header(Header::new("X-GitHub-Delivery", "0000"));
        request.add_header(Header::new("X-Hub-Signature", format!("sha1={}", result)));
        let mut response = request.dispatch_with(&rocket);
        assert_eq!(response.status(), Status::Ok);
        assert_eq!(response.body().and_then(|f| f.into_string()), Some("pong".into()));

        let mut request = MockRequest::new(Post, "/changelogs").body(&json);
        request.add_header(ContentType::JSON);
        request.add_header(Header::new("X-GitHub-Event", "ping"));
        request.add_header(Header::new("X-GitHub-Delivery", "0000"));
        request.add_header(Header::new("X-Hub-Signature", format!("sha1={}", result)));
        assert_eq!(request.dispatch_with(&rocket).status(), Status::NotFound);

        let mut request = MockRequest::new(Post, "/changelog").body(&json);
        request.add_header(ContentType::JSON);
        request.add_header(Header::new("X-GitHub-Event", "ping"));
        request.add_header(Header::new("X-GitHub-Delivery", "0000"));
        request.add_header(Header::new("X-Hub-Signature", format!("sha2={}", result)));
        assert_eq!(request.dispatch_with(&rocket).status(), Status::NotImplemented);

        let mut request = MockRequest::new(Post, "/changelog").body(&json);
        request.add_header(ContentType::JSON);
        request.add_header(Header::new("X-GitHub-Event", "ping"));
        request.add_header(Header::new("X-GitHub-Delivery", "0000"));
        request.add_header(Header::new("X-Hub-Signature", "sha1=0000000000000000000000000000000000000000"));
        assert_eq!(request.dispatch_with(&rocket).status(), Status::Forbidden);

        let mut request = MockRequest::new(Post, "/changelog").body(&json);
        request.add_header(ContentType::JSON);
        request.add_header(Header::new("X-GitHub-Event", "ping"));
        request.add_header(Header::new("X-GitHub-Delivery", "0000"));
        request.add_header(Header::new("X-Hub-Signature", "sha1=00000"));
        assert_eq!(request.dispatch_with(&rocket).status(), Status::BadRequest);

        let mut request = MockRequest::new(Post, "/changelog").body(&  json);
        request.add_header(ContentType::JSON);
        assert_eq!(request.dispatch_with(&rocket).status(), Status::BadRequest);
    }
}
