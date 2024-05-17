# put all of the files from this project into a folder.a
# enter that folder in your shell session
# run the command: docker image build -t jvuebot:0.0.10
# the name jvuebot is arbitrary, and the build number is arbitrary
# now you have a docker image in your local repo, that you can use to run a container.a
# whenever you want to change the configuration, you'll have to remove and rebuild the image/container.
# will work on changing this to use editable environment variables in the future

FROM python:latest

LABEL Maintainer="Jomack16"

WORKDIR /config

# COPY JVueBot.py config.py requirements.txt ./config

COPY JVueBot.py /config

COPY config.py /config

COPY requirements.txt /config

RUN pip install -r /config/requirements.txt

CMD ["python", "JVueBot.py"]
