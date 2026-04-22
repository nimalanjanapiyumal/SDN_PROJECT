# OpenStack Quick Configuration

The OpenStack page in the dashboard works in either of these modes:

## Option A: clouds.yaml (recommended)
Create `~/.config/openstack/clouds.yaml`:

```yaml
clouds:
  mycloud:
    auth:
      auth_url: http://<keystone-host>:5000/v3
      username: <username>
      password: <password>
      project_name: <project>
      user_domain_name: Default
      project_domain_name: Default
```

Then run:
```bash
export OS_CLOUD=mycloud
```

## Option B: environment variables
```bash
export OS_AUTH_URL=http://<keystone-host>:5000/v3
export OS_USERNAME=<username>
export OS_PASSWORD=<password>
export OS_PROJECT_NAME=<project>
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
```

Once configured, refresh the OpenStack page to view server and network visibility.
