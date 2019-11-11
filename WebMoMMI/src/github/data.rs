#[derive(Deserialize, Debug, Clone)]
pub struct PullRequestEvent {
    pub action: PullRequestAction,
    pub number: u32,
    pub pull_request: PullRequest,
    pub repository: Repository,
}

#[derive(Deserialize, Debug, Clone)]
pub struct PushEvent {
    pub commits: Vec<PushedCommit>,
    pub repository: Repository,
}

#[derive(Deserialize, Debug, Clone)]
pub struct Repository {
    pub full_name: String,
}

#[derive(Deserialize, Debug, Clone)]
pub struct PushedCommit {
    pub added: Vec<String>,
    pub modified: Vec<String>,
}

#[derive(Deserialize, Serialize, Copy, Clone, Eq, PartialEq, Debug)]
#[serde(rename_all = "snake_case")]
pub enum PullRequestAction {
    Assigned,
    Unassigned,
    ReviewRequested,
    ReviewRequestRemoved,
    Labeled,
    Unlabeled,
    Opened,
    Edited,
    Closed,
    Reopened,
    Synchronize,
    Locked,
    Unlocked
}

#[derive(Deserialize, Debug, Clone)]
pub struct PullRequest {
    pub merged: bool,
    pub body: String,
    pub user: GitHubUser,
}

#[derive(Deserialize, Debug, Clone)]
pub struct GitHubUser {
    pub login: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deserialize() {
        let test_string = r#"
{
    "action": "opened",
    "number": 123,
    "pull_request": {
        "merged": false,
        "body": "honk",
        "user": {
            "login": "PJB3005"
        }
    },
    "repository": {
        "full_name": "PJB3005/MoMMI"
    }
}"#;

        let deserialized = serde_json::from_str::<PullRequestEvent>(test_string).unwrap();
        assert_eq!(deserialized.action, PullRequestAction::Opened);
        assert_eq!(deserialized.number, 123);
        assert_eq!(deserialized.pull_request.merged, false);
    }
}
