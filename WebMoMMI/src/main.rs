#![feature(plugin, custom_derive)]
#![plugin(rocket_codegen)]

extern crate rocket;
extern crate rocket_contrib;
extern crate serde;
#[macro_use] extern crate serde_derive;
#[macro_use] extern crate serde_json;
extern crate crypto;
extern crate byteorder;
extern crate rustc_serialize;

mod mommi;
mod github;

fn main() {
    rocket::ignite().mount("/", routes![mommi::get_nudgeold, mommi::get_nudge, github::post_github]).launch();
}
