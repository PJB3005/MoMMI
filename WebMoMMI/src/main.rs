#![feature(plugin, custom_derive)]
#![plugin(rocket_codegen)]

extern crate rocket;
extern crate rocket_contrib;
extern crate serde;
// #[macro_use]
// extern crate serde_derive;
#[macro_use]
extern crate serde_json;
extern crate crypto;
extern crate byteorder;
extern crate rustc_serialize;
#[macro_use]
extern crate lazy_static;
extern crate yaml_rust;

mod mommi;
mod github;

#[get("/twohundred")]
fn twohundred() -> &'static str {
    "hi BYOND!"
}

fn main() {
    rocket::ignite().mount("/", routes![twohundred, mommi::get_nudgeold, mommi::get_nudge, github::post_github]).launch();
}
