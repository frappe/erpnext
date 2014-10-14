#!/bin/bash

# stolen from http://cgit.drupalcode.org/octopus/commit/?id=db4f837
includedir=`mysql_config --variable=pkgincludedir`
thiscwd=`pwd`
_THIS_DB_VERSION=`mysql -V 2>&1 | tr -d "\n" | cut -d" " -f6 | awk '{ print $1}' | cut -d"-" -f1 | awk '{ print $1}' | sed "s/[\,']//g"`
if [ "$_THIS_DB_VERSION" = "5.5.40" ] && [ ! -e "$includedir-$_THIS_DB_VERSION-fixed.log" ] ; then
  cd $includedir
  sudo patch -p1 < $thiscwd/ci/my_config.h.patch &> /dev/null
  sudo touch $includedir-$_THIS_DB_VERSION-fixed.log
fi
