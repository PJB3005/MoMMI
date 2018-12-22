#![feature(proc_macro_hygiene, decl_macro)]

#[macro_use]
extern crate rocket;
#[macro_use]
extern crate serde_derive;

mod config;
mod github;
mod mommi;

use std::sync::Arc;

use crate::config::MoMMIConfig;

#[get("/twohundred")]
fn twohundred() -> &'static str {
    "hi BYOND!"
}

fn main() {
    let mut rocket = rocket::ignite();
    let config = match MoMMIConfig::new(rocket.config()) {
        Ok(x) => Arc::new(x),
        Err(x) => {
            println!("Failed to launch, broken config: {}", x);
            return;
        }
    };

    if config.has_commloop() {
        rocket = rocket.mount(
            "/",
            routes![mommi::get_nudgeold, mommi::get_nudge, mommi::get_nudge_new,],
        )
    }

    if config.has_github_key() || !config.verify_github() {
        rocket = rocket.mount(
            "/",
            routes![
                github::post_github,
                github::post_github_new,
                github::post_github_new_specific,
                github::post_github_alt,
            ],
        )
    }

    rocket.manage(config).launch();
}
