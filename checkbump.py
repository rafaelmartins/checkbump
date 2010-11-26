#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser
from contextlib import closing
from datetime import datetime
from subprocess import Popen, PIPE
from urllib2 import urlopen

from portage import portagetree
from portage.versions import pkgsplit, vercmp

import os, sys


class PackageException(Exception):
    pass


class Package(object):
    
    def __init__(self, atom, url):
        self.atom = atom
        self.url = url
        self.upstream_version = ''
        try:
            with closing(urlopen(url)) as fp:
                self._content = fp.read()
        except:
            raise PackageException('Fetch failed: %r' % url)
    
    @property
    def gentoo_version(self):
        portage = portagetree()
        versions = portage.dep_match(self.atom)
        if len(versions) == 0:
            raise PackageException('Package not found: %r' % self.atom)
        last_atom = versions[-1]
        cp, pv, rev = pkgsplit(last_atom)
        return pv
    
    @property
    def up2date(self):
        return vercmp(self.gentoo_version, self.upstream_version) == 0
    
    def run_command(self, command):
        p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(self._content)
        if p.returncode != os.EX_OK:
            raise PackageException('Command failed: %r' % command)
        self.upstream_version += stdout.strip()


class PackageList(list):
    
    def __init__(self, ini_file):
        self._parser = ConfigParser()
        parsed_file = self._parser.read(ini_file)
        if not len(parsed_file) == 1:
            raise PackageException('Failed to load config: %r' % ini_file)
        list.__init__(self)
        atoms = self._parser.sections()
        atoms.sort()
        for atom in atoms:
            print >> sys.stderr, 'Fetching: %s' % atom
            url = None
            commands = None
            for name, value in self._parser.items(atom):
                if name == 'url':
                    url = value
                elif name == 'command':
                    commands = value
            if url is None or commands is None:
                raise PackageException('Invalid url/command: %r' % atom)
            package = Package(atom, url)
            for command in commands.split('\n'):
                package.run_command(command.strip())
            self.append(package)


class HTMLReport(object):
    
    def __init__(self, ini_file):
        self._ini_file = ini_file
        self._pkg_list = PackageList(self._ini_file)
    
    def _header(self):
        return """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <title>Version bump checker</title>
        <meta http-equiv="content-type" content="text/html;charset=utf-8" />
    </head>
    <body>
        <h1>Version bump checker</h1>
        <table border="1">
            <tr>
                <th>Package</th>
                <th>Our version</th>
                <th>Upstream version</th>
                <th>Up-to-date?</th>
            </tr>

<!-- init packages -->

"""

    def _footer(self):
        return """\
        
<!-- end packages -->

        </table>
        <hr />
        <p>
            Last update: %s UTC
        </p>
    </body>
</html>
""" % datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    def _package(self, pkg):
        return """\
<tr>
    <td>%(atom)s</td>
    <td>%(gentoo_version)s</td>
    <td>%(upstream_version)s</td>
    <td bgcolor="%(color)s">%(up2date)s</td>
</tr>
""" % {
            'atom': pkg.atom,
            'gentoo_version': pkg.gentoo_version,
            'upstream_version': pkg.upstream_version,
            'color': pkg.up2date and 'green' or 'red',
            'up2date': pkg.up2date and 'Yes' or 'No',
        }

    def __str__(self):
        tmp = self._header()
        for pkg in self._pkg_list:
            tmp += self._package(pkg)
        tmp += self._footer()
        return tmp

    
if __name__ == '__main__':
    print HTMLReport('sci-electronics.ini')
