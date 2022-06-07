FROM python:3.5

RUN apt update && \
    apt install tini

COPY dist/WebTeachingEnvironment-1.3.3.tar.gz /tmp

RUN pip install pyramid_exclog psycopg2

RUN pip install /tmp/WebTeachingEnvironment-1.3.3.tar.gz

RUN mkdir /etc/wte

ENTRYPOINT ["tini", "--"]
CMD ["pserve", "/etc/wte/production.ini"]
