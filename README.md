# Interactive interpreter for Syberian Leninec II

[![DeepSource](https://deepsource.io/gh/hikariatama/leninec.svg/?label=active+issues&show_trend=true&token=IPVI_QX-cSuQSVeVl8cb5PLt)](https://deepsource.io/gh/hikariatama/leninec/?ref=repository-badge)  

[![DeepSource](https://deepsource.io/gh/hikariatama/leninec.svg/?label=resolved+issues&show_trend=true&token=IPVI_QX-cSuQSVeVl8cb5PLt)](https://deepsource.io/gh/hikariatama/leninec/?ref=repository-badge)  

![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/hikariatama/leninec)
![GitHub repo size](https://img.shields.io/github/repo-size/hikariatama/leninec)
![License](https://img.shields.io/github/license/hikariatama/leninec)
![Forks](https://img.shields.io/github/forks/hikariatama/leninec?style=flat)
![Stars](https://img.shields.io/github/stars/hikariatama/leninec?style=flat)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

![demo](https://user-images.githubusercontent.com/36935426/217303147-85bccced-3ed8-4e92-a524-59e6c296f425.png)

## Installation

### Docker

```bash
docker run --name leninec -d -p 2931:2931 ghcr.io/hikariatama/leninec:latest
```

### Manual

```bash
git clone https://github.com/hikariatama/leninec
cd leninec
pip install -r requirements.txt
cd server
uvicorn app:app --host 0.0.0.0 --port 2931
```

### Proxy-passing

In order for websockets to works correctly, copy the following router config to your server:

```nginx
    location /ws {
        proxy_pass http://127.0.0.1:2931;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
```
