FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --uid 10001 plnts

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY plnts_app.py .
COPY geoip/worldcities.csv geoip/worldcities.csv
COPY geoip/GeoLite2-City_20230908/GeoLite2-City.mmdb geoip/GeoLite2-City_20230908/GeoLite2-City.mmdb

USER plnts
EXPOSE 8080
ENV PORT=8080
CMD ["python", "plnts_app.py"]
