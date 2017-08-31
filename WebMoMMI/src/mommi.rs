//! Interfacing with MoMMIv2.

use std::net::{ToSocketAddrs, TcpStream};
use std::io::{Write, Error as IoError};
use serde::Serialize;
use crypto::sha2::Sha512;
use crypto::hmac::Hmac;
use crypto::mac::Mac;
use byteorder::{NetworkEndian, WriteBytesExt, ReadBytesExt};
use rocket::State;
use config::MoMMIConfig;

/// Sends a message to the MoMMI commloop.
/// Really can't get simpler than this.
pub fn commloop<A: ToSocketAddrs, S: Serialize>(
    address: A,
    password: &str,
    message_type: &str,
    meta: &str,
    content: S,
) -> Result<(), MoMMIError> {
    let json = json!({
        "type": message_type,
        "meta": meta,
        "cont": content
    }).to_string();

    let mut hmac = Hmac::new(Sha512::new(), password.as_bytes());
    hmac.input(json.as_bytes());
    let result = hmac.result();

    let mut socket = TcpStream::connect(address)?;
    socket.write_all(b"\x30\x05")?;
    socket.write_all(result.code())?;
    socket.write_u32::<NetworkEndian>(
        json.as_bytes().len() as u32,
    )?;
    socket.write_all(json.as_bytes())?;
    socket.flush()?;

    let code = socket.read_u8()?;

    match code {
        0 => Ok(()),
        x => Err(MoMMIError::from(x)),
    }
}

#[derive(Debug)]
pub enum MoMMIError {
    IdBytes,
    Json,
    Auth,
    Unknown,
    Io(IoError),
}

impl From<u8> for MoMMIError {
    fn from(code: u8) -> MoMMIError {
        match code {
            1 => MoMMIError::IdBytes,
            2 => MoMMIError::Json,
            3 => MoMMIError::Auth,
            _ => MoMMIError::Unknown,
        }
    }
}

impl From<IoError> for MoMMIError {
    fn from(error: IoError) -> MoMMIError {
        MoMMIError::Io(error)
    }
}


// Damnit past me for forcing current me to do this so future me has to clean it up sometime!

#[derive(Clone, Debug, FromForm)]
pub struct NudgeOld {
    admin: Option<bool>,
    pass: String,
    content: String,
    ping: Option<bool>,
}

#[derive(Clone, Debug, FromForm)]
pub struct Nudge {
    meta: String,
    pass: String,
    content: String,
}

// Kill this monstrosity.
// NOW.
impl From<NudgeOld> for Nudge {
    fn from(old: NudgeOld) -> Nudge {
        Nudge {
            meta: match old.admin {
                Some(true) => "admin".into(),
                _ => "regular".into(),
            },
            pass: old.pass,
            content: {
                if let Some(true) = old.ping {
                    old.content + "{{PING}}"
                } else {
                    old.content
                }
            },
        }
    }
}

// GET because >BYOND
#[allow(unmounted_route)]
#[get("/mommi?<nudge>")]
pub fn get_nudgeold(
    nudge: NudgeOld,
    config: State<MoMMIConfig>,
) -> Result<&'static str, MoMMIError> {
    get_nudge(nudge.into(), config)
}

#[allow(unmounted_route)]
#[get("/mommi?<nudge>", rank = 2)]
pub fn get_nudge(nudge: Nudge, config: State<MoMMIConfig>) -> Result<&'static str, MoMMIError> {
    let message = json!({
        "password": nudge.pass.clone(),
        "message": nudge.content.clone()
    });

    commloop(
        config.get_commloop_address(),
        config.get_commloop_password(),
        "gamenudge",
        &nudge.meta,
        &message,
    )?;
    Ok("MoMMI successfully received the message.")
}
