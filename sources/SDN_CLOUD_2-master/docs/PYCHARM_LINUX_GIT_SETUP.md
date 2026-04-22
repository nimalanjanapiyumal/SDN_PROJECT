# PyCharm + Ubuntu VM + Git Setup Guide

This guide shows the easiest way to work on this SDN project with:

- **PyCharm on your local machine** for editing
- **Ubuntu VM** for running Mininet, Ryu, Prometheus, and Grafana
- **Git** for version control and pushing to GitHub or GitLab

## Recommended workflow

For this project, the safest workflow is:

1. **Edit code in PyCharm** on your laptop or desktop.
2. **SSH into the Ubuntu VM** to install dependencies and run the stack.
3. **Use Git** to commit and push your work.

Why this layout?

- Mininet and Open vSwitch work best on **Ubuntu/Linux**.
- PyCharm is ideal for editing, search, refactoring, and Git history.
- The VM gives you a clean Linux runtime for SDN experiments.

## Option A: PyCharm Professional (best experience)

Use this option if you have **PyCharm Professional**.

You can:

- open the project locally,
- connect to the Ubuntu VM over SSH,
- use a **remote SSH interpreter**,
- open an SSH terminal inside PyCharm.

## Option B: PyCharm Community

Use this option if you have **PyCharm Community**.

You can still:

- open the project locally,
- edit all files normally,
- use the built-in terminal or an external terminal,
- SSH into the Ubuntu VM and run the project there.

The main difference is that the **SSH interpreter feature is part of PyCharm Professional**.

---

## 1. Prepare the Ubuntu VM

Log into the Ubuntu VM directly and run:

```bash
sudo apt update
sudo apt install -y openssh-server git curl
sudo systemctl enable --now ssh
hostname -I
```

Record the VM IP address that appears from `hostname -I`.

Check that SSH is listening:

```bash
sudo systemctl status ssh --no-pager
```

If you are using a VM platform with NAT networking, you may need a port forward for SSH. If you are using bridged networking, the VM usually gets its own LAN IP and you can connect directly.

## 2. Copy the project to the machine you will edit from

Place the ZIP bundle on your local machine and extract it.

Example:

```bash
unzip sdn_adaptive_cloud_bundle.zip
cd sdn_adaptive_cloud
```

If you prefer to keep the main working copy inside the Ubuntu VM, you can also copy it there with `scp` after extraction.

Example:

```bash
scp -r sdn_adaptive_cloud youruser@VM_IP:~
```

---

## 3. Open the project in PyCharm

### Open an extracted folder

In PyCharm:

- **File -> Open**
- select the `sdn_adaptive_cloud` folder
- open it as a project

### Or clone from Git later

If you push the repository first, you can also use:

- **VCS -> Get from Version Control**
- paste your Git URL
- choose the local destination folder

---

## 4. SSH into the Ubuntu VM

From a terminal on your local machine:

```bash
ssh youruser@VM_IP
```

If your VM uses a custom SSH port:

```bash
ssh -p 2222 youruser@127.0.0.1
```

After logging in, copy or clone the project into the VM home directory, for example:

```bash
cd ~
ls
```

---

## 5. Set up PyCharm to work with the VM

### If you have PyCharm Professional

#### Add an SSH configuration

In PyCharm:

- **Settings -> Tools -> SSH Configurations**
- add your VM host, port, username, and authentication method

#### Add an SSH interpreter

In PyCharm:

- **Settings -> Python Interpreter**
- click **Add Interpreter**
- choose **On SSH**
- select the VM connection

Use one of these interpreter paths:

- before project install: `/usr/bin/python3`
- after project install: `/home/youruser/sdn_adaptive_cloud/.venv/bin/python`

#### Open a terminal to the VM

In PyCharm:

- **Tools -> Start SSH Session**

That lets you edit in PyCharm and run commands inside the Ubuntu VM from the IDE.

### If you have PyCharm Community

Use PyCharm for editing only, then run commands from:

- the built-in terminal,
- your system terminal,
- or a separate SSH client.

You can keep the source code local and copy it to the VM, or keep the source code in Git and pull it into the VM.

---

## 6. Configure Git

Run this once on the machine where you want to make commits:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Check it:

```bash
git config --global --list
```

---

## 7. Create an SSH key for GitHub or GitLab

If you want passwordless Git pushes over SSH:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```

Copy the printed public key and add it to your Git hosting account.

### GitHub test

```bash
ssh -T git@github.com
```

### GitLab test

```bash
ssh -T git@gitlab.com
```

---

## 8. Initialize the repository and connect a remote

This project now includes a helper script:

```bash
bash scripts/git_bootstrap.sh main git@github.com:YOUR_USER/YOUR_REPO.git
```

What it does:

- initializes Git if needed,
- renames the branch to `main`,
- creates the first commit if the repo is empty,
- adds `origin` if you passed a remote URL,
- pushes to the remote.

### Manual Git commands

If you prefer to do it yourself:

```bash
git init
git add .
git commit -m "Initial commit: SDN adaptive cloud framework"
git branch -M main
git remote add origin git@github.com:YOUR_USER/YOUR_REPO.git
git push -u origin main
```

To check the configured remote:

```bash
git remote -v
```

---

## 9. Install and run the project inside Ubuntu

Once the source is inside the Ubuntu VM:

```bash
cd ~/sdn_adaptive_cloud
bash scripts/install_ubuntu.sh
bash scripts/start_all.sh
bash scripts/run_topology.sh --foreground --scenario mixed --cli
```

Open these in a browser:

- Prometheus: `http://VM_IP:9090`
- Grafana: `http://VM_IP:3000`
- Controller API: `http://VM_IP:8080/api/v1/state`

If the VM is using NAT and these ports are not reachable from your host, create port forwards in the VM manager.

---

## 10. Daily development flow

### Local PyCharm + VM + Git

1. Open the project in PyCharm.
2. Start an SSH session to the VM.
3. Pull the latest code:

```bash
git pull
```

4. Edit code in PyCharm.
5. Run the stack in the VM.
6. Commit changes:

```bash
git add .
git commit -m "Describe your change"
git push
```

---

## 11. Common problems

### The `On SSH` interpreter option is missing in PyCharm

You are most likely using **PyCharm Community**. Use the VM through a normal SSH terminal instead.

### `Permission denied (publickey)` when pushing Git

Check:

- your public key was added to GitHub or GitLab,
- the SSH agent is running,
- your remote URL uses SSH and not HTTPS.

Check the remote URL:

```bash
git remote -v
```

### Mininet fails unless you use `sudo`

That is expected for many Mininet actions. Use the provided scripts exactly as documented, because `run_topology.sh` already launches the topology with `sudo`.

### Grafana or Prometheus do not open from your host machine

Usually this is a VM networking issue. Use one of these:

- bridged adapter,
- NAT with port forwarding,
- host-only plus explicit routing.

### PyCharm created `.idea/` files

That is normal. The project `.gitignore` now ignores `.idea/` and common IDE files.

---

## 12. Recommended clean setup path

If you want the easiest working setup, do this in order:

1. Extract the ZIP on your local machine.
2. Open it in PyCharm.
3. Ensure the Ubuntu VM has SSH enabled.
4. Copy the folder to the VM with `scp`, or push it to Git and clone it in the VM.
5. Run `bash scripts/install_ubuntu.sh` inside the VM.
6. If you have PyCharm Professional, add the VM as an SSH interpreter.
7. Commit and push regularly with Git.

---

## References

- JetBrains PyCharm Documentation, *Open, reopen, and close projects*.
- JetBrains PyCharm Documentation, *Configure a Python interpreter*.
- JetBrains PyCharm Documentation, *Configure an interpreter using SSH*.
- JetBrains PyCharm Documentation, *Run SSH terminal*.
- Git Project, *First-Time Git Setup*.
- Git Project, *Getting a Git Repository*.
- Git Project, *Working with Remotes*.
- GitHub Docs, *Generating a new SSH key and adding it to the ssh-agent*.
- GitHub Docs, *Adding a new SSH key to your GitHub account*.
