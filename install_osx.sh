#!/bin/bash

# Install HomeBrew
if [ -x "$(brew)" ]; then
  /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
fi

brew install postgresql
# brew services postgresql start
brew install redis
# brew services redis-server start
brew install python3

pip install virtualenvwrapper

source /usr/local/bin/virtualenvwrapper.sh

rmvirtualenv zenhub_cycle_time
mkvirtualenv --python=$(which python3.6) zenhub_cycle_time
workon zenhub_cycle_time
setvirtualenvproject
pip install -r requirements/base.txt
echo "DEBUG = True" > issues/settings_local.py

echo "Github token: "
read github_token

echo "Github username or organization name: "
read user

echo "Zenhub token: "
read zenhub_token

cat >issues/credentials.py <<EOL
GITHUB = {'token': '$github_token', 'owner': '$user'}
ZENHUB = {'token': '$zenhub_token'}
EOL

dropdb issue_tracker
createdb issue_tracker
./manage.py migrate

./manage.py fetch --initial

./manage.py runserver
