# VotONG

[![GitHub contributors][ico-contributors]][link-contributors]
[![GitHub last commit][ico-last-commit]][link-last-commit]
[![License: MPL 2.0][ico-license]][link-license]

[See the project live][link-production]

The VotONG platform is a redeployment of a previous Code for Romania application,
[RoHelp](https://github.com/code4romania/ro-help).
The current code base is modified to allow the representatives of NGOs and Associations within the Civic Society
to nominate candidates and vote for them in several rounds of elections.

The vote implemented here is non-secret and is visible to the technical administrators of the platform.
This codebase shouldn't be used for any purpose that requires a secret vote,
not any purpose that requires a zero trust system.

The platform is designed to be used alongside
[NGO Hub](https://github.com/code4romania/onghub),
a platform for NGOs and Associations to gain access to different solutions and services provided by
[Commit Global][link-commit-global]
and
[Code for Romania][link-code4].
Sign-up and login are done through NGO Hub via Cognito,
but the platform can be used independently by changing the Django Allauth configuration.

[Contributing](#contributing) | [Built with](#built-with) | [Feedback](#feedback) | [License](#license) | [About Code4Ro](#about-code-for-romania)

## Contributing

This project is built by amazing volunteers, and you can be one of them!
Here's a list of ways in
[which you can contribute to this project][link-contributing].
If you want to make any change to this repository, please **make a fork first**.

Help us out by testing this project in the
[staging environment][link-staging].
If you see something that doesn't quite work the way you expect it to,
[open an Issue](https://github.com/code4romania/votong/issues/new/choose).
Make sure to describe what you _expect to happen_ and _what is actually happening_ in detail.

If you would like to suggest new functionality, open an Issue and mark it as a __[Feature request]__.
Please be specific about why you think this functionality will be of use.
Please include some visual description of what you would like the UI to look like if you’re suggesting new UI elements.

## Built With

* Django 4.2 (LTS)
* Bulma

### Programming languages

* Python (3.12+)

### Platforms

* Web

### Frontend framework

None. Includes Bulma for styling.

### Package managers

* Pip

### Database technology & provider

* PostgreSQL

### Pre-requisites

To run the project locally, you need to have
[Docker](https://docs.docker.com/get-docker/)
and the
[docker compose](https://docs.docker.com/compose/) plugin installed.

### Initial set-up

Initialize the environment variables:

```bash
cp .env.example .env
```

Check the `.env` file
and see if there are any environment variables that you might need to provide a value for or change.
This file is used by `docker compose` to pass the environment variables to the container it creates.

### Starting the project with Docker

Get the project up and running:

```bash
make rund-psql
# or
docker compose up -d --build
```

You should be able to access the local environment site and admin at the following URLs:

- <http://localhost:8030/>
- <http://localhost:8030/admin/>

Some dummy data is loaded automatically when starting the containers for the first time.

You can access the admin with email `admin@example.com` and password `secret`
(all automatically created users in the dev environment have the password set to `secret`).

If you have problems starting the project, first check out the
[FAQ](https://github.com/code4romania/votong/wiki/FAQ)
and if that doesn't work, ask someone from the project's channel.
It would help a lot if you could also add the issue to the
[FAQ](https://github.com/code4romania/votong/wiki/FAQ).

To work on running containers that were started using `docker compose up`,
run the following command:

```bash
docker compose exec web bash
```

**IMPORTANT**: Remember to run `make format` before commiting your code to format the code properly. Thank you!

**NOTE** After the first deployment go into admin
and edit the site data in `/admin/sites/site/` with the correct name and domain.
This is used in the site and in email templates.

## Feedback

* Request a new feature on GitHub.
* Vote for popular feature requests.
* File a bug in GitHub Issues.
* Email us with other feedback contact@code4.ro

## License

This project is licensed under the MPL 2.0 License – see the [LICENSE](LICENSE) file for details

## About Code for Romania

Started in 2016, Code for Romania is a civic tech NGO, official member of the Code for All network.
We have a community of over 500 volunteers
(developers, ux/ui, communications, data scientists, graphic designers, devops, IT security, and more)
who work pro bono for developing digital solutions to solve social problems.
#techforsocialgood.
If you want to learn more details about our projects
[visit our site](https://www.code4.ro/)
or if you want to talk to one of our staff members, please e-mail us at
[contact@code4.ro](mailto:contact@code4.ro).

Last, but not least, we rely on donations to ensure the infrastructure, logistics, and management of our community
that is widely spread across 11 timezones,
coding for social change to make Romania and the world a better place.
If you want to support us, [you can do it here][link-donate].

[ico-contributors]: https://img.shields.io/github/contributors/code4romania/votong.svg?style=for-the-badge

[ico-last-commit]: https://img.shields.io/github/last-commit/code4romania/votong.svg?style=for-the-badge

[ico-license]: https://img.shields.io/badge/license-MPL%202.0-brightgreen.svg?style=for-the-badge

[link-contributors]: https://github.com/code4romania/standard-repo-template/graphs/contributors

[link-last-commit]: https://github.com/code4romania/standard-repo-template/commits/main

[link-license]: https://opensource.org/licenses/MPL-2.0

[link-contributing]: https://github.com/code4romania/.github/blob/main/CONTRIBUTING.md

[link-production]: https://votong.ro/

[link-staging]: https://votong.staging.heroesof.tech/

[link-commit-global]: https://commitglobal.org/

[link-code4]: https://www.code4.ro/en/

[link-donate]: https://www.code4.ro/ro/doneaza
