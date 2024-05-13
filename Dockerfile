FROM testbox

RUN apt-get install -y nasm
RUN apt-get install -y unzip

WORKDIR /test
ENV PYTHONPATH /test:${PYTHONPATH}

COPY . .

RUN python3 -m tools.build
RUN unzip UltimaVI-ru.zip 
RUN rm UltimaVI-ru.zip
RUN mv UltimaVI-ru/* .
RUN rmdir UltimaVI-ru

COPY tools/RK.COM .
COPY tools/RUSSIAN.RK .
COPY tools/8X16.RK .

ENTRYPOINT ["python3", "-m", "unittest", "-v"]
