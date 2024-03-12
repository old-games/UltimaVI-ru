FROM testbox

RUN apt-get install -y nasm
RUN apt-get install -y unzip

WORKDIR /app
ENV PYTHONPATH /app:${PYTHONPATH}
COPY . .

WORKDIR /test
RUN python3 -m tools.build
RUN unzip -j UltimaVI-ru.zip 
RUN rm UltimaVI-ru.zip

COPY tools/RK.COM .
COPY tools/RUSSIAN.RK .
COPY tools/8X16.RK .

COPY screenshots screenshots

CMD python3 -m tools.test
