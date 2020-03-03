# tower-analytics-test-data

![Python application](https://github.com/jameswnl/tower-analytics-test-data/workflows/Python%20application/badge.svg)

API to generate test data for Automation Analytics


## Env variables

```
  # path to folder to store created bundles
  BUNDLE_DIR  # Default: /BUNDLE_DIR'
  
  # host url this service is exposed. The service in K8s pod
  # This will be where client(processor) can download the bundles
  HOST_URL
```

### Authentication
To guard the API service using GitHub OAuth app https://github.com/settings/applications

```
   GH_AUTH_CLIENT_ID  # Github OAuth App client ID
   GH_AUTH_CLIENT_SECRET  # Github OAuth App client Secret
   ALLOW_GH_ORGS  # Allowed Github organizations. Default: Ansible
```
