# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8

ENV DEBIAN_FRONTEND=noninteractive 

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

# ARG USERNAME=vscode
# ARG USER_UID=1000
# ARG USER_GID=$USER_UID
# ENV PIP_TARGET=/usr/local/share/pip-global
# ENV PYTHONPATH=${PYTHONPATH}:${PIP_TARGET}
# ENV PATH=${PATH}:${PIP_TARGET}/bin

# Prep container env
# Configure apt and install packages
RUN apt-get update \
    && apt-get -y install --no-install-recommends apt-utils dialog 2>&1 \
    #
    # Verify git, process tools, lsb-release (common in install instructions for CLIs) installed
    && apt-get -y install git iproute2 procps lsb-release \
    #
    # Install pylint
    && pip --disable-pip-version-check --no-cache-dir install pylint \
    #
    # Update Python environment based on requirements.txt
    #&& pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    #&& rm -rf /tmp/pip-tmp \
    #
    # Create a non-root user to use if preferred - see https://aka.ms/vscode-remote/containers/non-root-user.
    #&& groupadd --gid $USER_GID $USERNAME \
    #&& useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    # [Optional] Add sudo support for the non-root user
    #&& apt-get install -y sudo \
    #&& echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME\
    #&& chmod 0440 /etc/sudoers.d/$USERNAME \
    #
    # Create alternate global install location that both uses have rights to access
    #&& mkdir -p /usr/local/share/pip-global \
    #&& chown ${USERNAME}:root /usr/local/share/pip-global \
    #
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*
    
ENV DEBIAN_FRONTEND=dialog

# Install pip requirements
ADD requirements.txt .
RUN python -m pip install -r requirements.txt 

# allows us to compile tsdb for loading pre-historic animal data into prometheus with joy
RUN wget https://dl.google.com/go/go1.14.4.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.14.4.linux-amd64.tar.gz
RUN export PATH=$PATH:/usr/local/go/bin

# allows us to hang our heads in shame as we can't set env vars
ENV GO111MODULE=on

# allows us to install the worlds absolute best build and package tool.  ever. 
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list
RUN apt update && apt install -y yarn

EXPOSE 8000
WORKDIR /app
ADD . /app

# During debugging, this entry point will be overridden. For more information, refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "main.py"]
