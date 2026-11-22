# PLNTS

Curl-friendly planet rise/set times in UTC (wttr.in-style), for the observer's location.

## Usage

```bash
curl https://plnts.claviusimaging.com/
curl 'https://plnts.claviusimaging.com/?city=Melbourne'
curl 'https://plnts.claviusimaging.com/?lat=-37.8&lon=144.9'
```

- Default: GeoLite2 IP geolocation (lat/lon from the MMDB).
- Behind nginx, send `X-Real-IP` so the app sees the client address.
- `?city=` looks up `geoip/worldcities.csv` (loaded once at startup).
- `?lat=` + `?lon=` set the observer directly.

## Run with Docker

```bash
docker build -t plnts .
docker run --rm -p 127.0.0.1:8080:8080 plnts
```

Env overrides: `PLNTS_MMDB`, `PLNTS_CITIES`, `PORT`, `PLNTS_HOST`.

## GeoLite2

This product includes GeoLite2 Data created by MaxMind, available from https://www.maxmind.com/.

The City MMDB in `geoip/` is free. Optional updates need a free MaxMind account; not required to run.
