# Izuna YTDLaaS

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://travis-ci.org/username/repo.svg?branch=master)](https://travis-ci.org/username/repo)
[![Coverage Status](https://coveralls.io/repos/github/username/repo/badge.svg?branch=master)](https://coveralls.io/github/username/repo?branch=master)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Youtube Downloader as a Service.
This project is created as a companion service to [Izuna](https://github.com/arung-agamani/izuna), serving additional features for downloading Youtube file and converting into desired format, and hosting the final file to AWS S3

## Table of Contents

-   [Installation](#installation)
-   [Usage](#usage)
-   [Features](#features)
-   [Contributing](#contributing)
-   [License](#license)

## Installation

To use this project, you'll need:

-   Python 3.9 and above
    -   If you don't have Python installed, download it from the official website: [Python Downloads](https://www.python.org/downloads/)
-   Poetry package manager
    -   If you don't have Poetry installed, you can install it using the following command:
        ```
        curl -sSL https://install.python-poetry.org | python3 -
        ```
        For other installation methods, refer to the [Poetry documentation](https://python-poetry.org/docs/#installation).
    -   Run `poetry install`
-   Poe task runner
    -   Install via https://github.com/nat-n/poethepoet
-   Python packages
    As this project is using Poetry, the list of packages are already listed in `pyproject.toml`. Simply run `poetry install` to install the dependencies.
-   `ffmpeg` binary
    -   Install it via package managers like `apt` (for Debian-based systems) or other means based on your operating system.
    -   Example for Debian-based systems:
        ```
        sudo apt install ffmpeg
        ```
-   Setup pre-commit
    -   Run `poetry run pre-commit install` to setup pre-commit hooks.

Ensure that `ffmpeg` is accessible in your system's PATH.

Once you have Python, Poetry, `yt-dlp`, and `ffmpeg` set up, you're ready to use this project.

## Usage

The following command will run the web server that will accept requests.

```
poe run
```

As this will run a Flask web server, you can customize the arguments, or even use WSGI server like `gunicorn` to run it. Further instruction for this will be released in next iteration.

Additionally, `docker-compose.yaml` is provided for quickly running the project. Firstly build the docker image for this project with tag `izuna-ytdl:latest` as it's referenced in compose file.

### Required Environment Variables

The following section describes the required environment variables to run this application.
| Environment Variable | Description | Data Type | Required |
|----------------------|-------------------------------------------------|------------|----------|
| YTDL_BUCKET_NAME | AWS S3 bucket name used in the service | String | Yes |
| JWT_NO_HIMITSU | Secret key for JWT authentication | String | Yes |
| KAKUSU_HIMITSU | Secret key used by Flask for session encryption | String | Yes |
| AWS_ACCESS_KEY | Access Key used by `boto3` to authenticate to AWS | String | Yes |
| AWS_SECRET_KEY | Secret key used by `boto3` to authenticate to AWS | String | Yes |
| AWS_REGION | Region where the S3 bucket is hosted | String | Yes |
| MAX_USER_TASK | Integer denoting the maximum download task a standard user can have | Integer | Yes |
| MASTER_SIGNUP_CODE | Signup code used to register new user | String | Yes |
| MASTER_TOKEN | Some weird token | String | No |
| DB_CONNECTION_URL | PostgreSQL Database connection string | String | Yes |

## Features

Youtube Downloader as a Service

-   Download a Youtube video and convert it into your desired format. Currently configured to produce mp3 audio only.
-   Web Interface. If you want to deploy as a standalone application, then web interface is [COMING SOON]
-   Upload the result to external destination. Currently targeting AWS S3

## Contributing

To contribute to this project, follow these steps:

1. Fork the repository to your own GitHub account.
2. Clone the forked repository to your local machine.
3. Set up the development environment by installing the required dependencies. See the Installation section for details.
4. Create a new branch for your contribution.
5. Make your changes
6. Commit your changes and push them to your forked repository.
   Submit a pull request to the master branch of this repository.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT). See the `LICENSE` file for more details.

<!-- ## Additional Sections (Optional)

You can include additional sections as per your project's needs. Here are a few examples:

### Documentation

Provide links to the project's documentation, if available.

### Roadmap

Outline the project's roadmap, future features, or planned updates. -->

## Authors

-   Arung Agamani (arung-agamani)
-   Ridho Pratama (ridho9)

## Acknowledgements

-   ChatGPT for assisting on writing this README.md
