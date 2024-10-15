# Contributing

This project is immense, and not everytime the working staff can work on it. It's a project born for the students by the students, so every possible help is appreciated. Do you feel like helping out? Just follow this guide in order to know how you can contribute!

Contributing can be done via **GitHub**, so you might want to know a bit of the basics of it (mainly what's **Git**, how to **fork** and **clone** a repo, what are **commits** and **pull requests**). If you don't feel like doing it from the **CLI** (Command Line Interface), you can do it via VSCode or any editor that you may prefer. Here, we'll tell you how to do it via a CLI, so that at the end you'll also have some take-home knowledge of how **Git** works.

{{% hint info %}}
<i class="fa-solid fa-circle-info" style="color: #74C0FC;"></i> **Pull Request's Rules & Help Contributing**

You can find more info about how to do a correct pull request [**here**](https://github.com/sapienzastudentsnetwork/sapienzastudentsnetwork.github.io/pulls)

If you're not familiar with **git** and **GitHub**, you can follow [GitHub's guide](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) on how to contribute to other's projects, or eventually ask help to the [project's staff](../contacts) or in one of the [available groups](../../channels/groups).
{{% /hint %}}

## Clone the project

In order to contribute to the development of the site, you must create a **fork** of the project and edit it. Once you make your edit, you can open a **pull request** and send your edits to us. Let's see how to do this:

1. On GitHub, open the [**repository page of the site**](https://github.com/sapienzastudentsnetwork/sapienzastudentsnetwork.github.io) and create a fork via the button on the top right. You can call it however you want, it won't impact the original repo;
2. Once your fork finished being created, you have to **clone it locally**. Before actually cloning it, you must copy the address of the repository: on the page of the fork that you just created, click on the green "**<i class="fa-solid fa-code" style="color: #63E6BE;"></i> Code**" button that you can find on the top of the page, and copy the `https` URL that should end in `.git` from the newly opened pop-up;
3. Open a terminal and navigate on a folder where you want to clone the fork. Once you decided a folder, type `git clone --recurse-submodules` and then paste your URL after the command. You'll see something like:
```bash
git clone --recurse-submodules https://github.com/<your_username>/<fork_name>.git
```
Now you cloned the fork locally, meaning that by opening up a text editor you can start editing the files of the site

## Start the site locally

There are currently three ways to run the site locally. One is by using the **Hugo binaries**, one by using **Docker**, and another is by using **Docker Compose**. Although they provide the same functions, Docker/Docker Compose might be a hard tool if you're using it for the first time. We encourage you to try it, but if you don't feel like it you can just use the Hugo binary:

{{% tabs "runningsite" %}}
{{% tab "🌐 Hugo" %}}
## Using Hugo

Before starting, check if you have the [Hugo binaries](https://gohugo.io/installation/) installed.

4. While still being on the folder of the repo, you can run locally the site by doing
```bash
hugo server
```
{{% hint warning %}}
<i class="fa-solid fa-triangle-exclamation" style="color: #FFD43B;"></i> **Warning**

If you received an error like the following
```txt
Error: error building site: process: readAndProcessContent: "/home/<user>
/SapienzaStudentsNetworkFork/it/canali/discord.md:7:1": failed to extract
shortcode: template for shortcode "button" not found
```
then it means that the theme of the site wasn't cloned succesfully. In order to fix this, you have two ways:
1. Remove from Git the folder of the theme with
 ```bash
 git rm themes/hugo-book
 ```
2. Remove the folder of the theme. On UNIX-like systems, it would be
 ```bash
 rm -rf themes/hugo-book
 ```
3. Install the theme again with Git, by using the following command:
```bash
git submodule add https://github.com/alex-shpak/hugo-book themes/hugo-book
```
Now the problem should have disappeared, and you should be able to build without problems the site.
{{% /hint%}}

5. Open [`localhost:1313`](http://localhost:1313/) on your browser and there you go! You can now live preview the site. Since Hugo supports hot reloading, everytime a file changes, the site will too.

6. If you want to stop the server, just press `Ctrl + C` in the terminal.

{{% /tab %}}
{{% tab "🐋 Docker" %}}
## Using Docker

Before starting, check if you have [**Docker**](https://www.docker.com/) installed.

4. In order to run the site locally and test your code, run the following commands:
```bash
docker build -t hugo-site . # Just the first time that you clone the fork
sudo docker run --rm -p 1313:1313 -v $(pwd):/app hugo-site # Everytime that you work on the project
```

5. Open [`localhost:1313`](http://localhost:1313/) in the browser, and there you go! You can now preview the site.
6. If you want to stop the server, just press `Ctrl+C` in the terminal.
{{% /tab %}}

{{% tab "🐋 Docker Compose" %}}
## Using Docker Compose

Before starting, check if you have [**Docker**](https://www.docker.com/) and [**Docker Compose**](https://docs.docker.com/compose/install/) installed.

4. In order to run the site locally and test your code, run the following commands:
```bash
docker compose up -d --build
```

5. Open [`localhost:1313`](http://localhost:1313/) in the browser, and there you go! You can now preview the site.

6. If you want to stop the server, run the command:
```bash
docker compose down
```

{{% hint info %}}
<i class="fa-solid fa-circle-info" style="color: #74C0FC;"></i> **Note**
If you want to see the logs of the server, you can run the command `docker compose logs -f`.
{{% /hint %}}

{{% /tab %}}

{{% /tabs %}}


## Proposals / Bugs

If you have any suggestions for making the site better, or you want to signal a bug, you can open an [issue](https://github.com/sapienzastudentsnetwork/sapienzastudentsnetwork.github.io/issues) on the GitHub repository (**NOT** on your fork!). Thank you in advance for any help you may give us!