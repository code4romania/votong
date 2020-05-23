# Civil Society Vote

[![GitHub contributors](https://img.shields.io/github/contributors/code4romania/civil_society_vote.svg?style=for-the-badge)](https://github.com/code4romania/civil_society_vote/graphs/contributors) [![GitHub last commit](https://img.shields.io/github/last-commit/code4romania/civil_society_vote.svg?style=for-the-badge)](https://github.com/code4romania/civil_society_vote/commits/master) [![License: MPL 2.0](https://img.shields.io/badge/license-MPL%202.0-brightgreen.svg?style=for-the-badge)](https://opensource.org/licenses/MPL-2.0)

The Civil Society Voting platform is a redeployment of a previous Code for Romania application, [RoHelp](https://github.com/code4romania/ro-help). The current code base is modified in order to serve a different purpose, namely allowing the representatives of NGOs and Associations within the Civic Society to nominate candidates and vote for them in several rounds of elections.

The vote implemented here is non-secret and is visible to the technical administrators of the platform. This codebase should not be used for any purpose that requires secret vote, not any purpose that requires a zero trust system.

[Contributing](#contributing) | [Built with](#built-with) | [Repos and projects](#repos-and-projects) | [Deployment](#deployment) | [Feedback](#feedback) | [License](#license) | [About Code4Ro](#about-code4ro)

## Contributing

This project is built by amazing volunteers and you can be one of them! Here's a list of ways in [which you can contribute to this project](.github/CONTRIBUTING.md). If you want to make any change to this repository, please **make a fork first**.

Help us out by testing this project in the [staging environment](INSERT_LINK_HERE). If you see something that doesn't quite work the way you expect it to, open an Issue. Make sure to describe what you _expect to happen_ and _what is actually happening_ in detail.

If you would like to suggest new functionality, open an Issue and mark it as a __[Feature request]__. Please be specific about why you think this functionality will be of use. If you can, please include some visual description of what you would like the UI to look like, if you are suggesting new UI elements.

## Built With

* Django
* Bulma

### Programming languages

* Python (3.6+)

### Platforms

* Web

### Frontend framework

None. Includes Bulma for stilying.

### Package managers

* Pip

### Database technology & provider

* PostgreSQL

### Pre-requisites

In order to run the project locally, you need to have [Docker](https://docs.docker.com/get-docker/) and [docker-compose](https://docs.docker.com/compose/) installed.

### Initial set-up

Initialize the environment variables:

```bash
cp .env.example .env
```

Check the `.env` file and see if there are any environment variables that you might need to provide a value for or change. This file is used by `docker-compose` to pass the environment variables to the container it creates.

### Starting the project

Get the project up and running:

```bash
docker-compose build
docker-compose up
```

You should be able to access the local environment site and admin at the following URLs:

- <http://localhost:8000/>
- <http://localhost:8000/admin/>

If you have problems starting the project, first check out the [FAQ](https://github.com/code4romania/civil_society_vote/wiki/FAQ) and if that doesn't work, ask someone from the project's channel.
Maybe the issue you just had is worth adding to the [FAQ](https://github.com/code4romania/civil_society_vote/wiki/FAQ), wouldn't it?

To work on running containers that were started using `docker-compose up`, open another terminal and:

```bash
cd path/to/repo
docker-compose exec web bash
```

## Deployment

Guide users through getting your code up and running on their own system. In this section you can talk about:
1. Installation process
2. Software dependencies
3. Latest releases
4. API references

Describe and show how to build your code and run the tests.

## Feedback

* Request a new feature on GitHub.
* Vote for popular feature requests.
* File a bug in GitHub Issues.
* Email us with other feedback contact@code4.ro

## License

This project is licensed under the MPL 2.0 License - see the [LICENSE](LICENSE) file for details

## About Code4Ro

Started in 2016, Code for Romania is a civic tech NGO, official member of the Code for All network. We have a community of over 500 volunteers (developers, ux/ui, communications, data scientists, graphic designers, devops, it security and more) who work pro-bono for developing digital solutions to solve social problems. #techforsocialgood. If you want to learn more details about our projects [visit our site](https://www.code4.ro/en/) or if you want to talk to one of our staff members, please e-mail us at contact@code4.ro.

Last, but not least, we rely on donations to ensure the infrastructure, logistics and management of our community that is widely spread across 11 timezones, coding for social change to make Romania and the world a better place. If you want to support us, [you can do it here](https://code4.ro/en/donate/).
