# repoclosure.py
# DNF plugin adding a command to display a list of unresolved dependencies
# for repositories.
#
# Copyright (C) 2015 Igor Gnatenko
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import dnf
import dnf.cli
import dnfpluginsextras

_ = dnfpluginsextras._


class RepoClosure(dnf.Plugin):

    name = "repoclosure"

    def __init__(self, base, cli):
        super(RepoClosure, self).__init__(base, cli)
        if cli is None:
            return
        cli.register_command(RepoClosureCommand)


class RepoClosureCommand(dnf.cli.Command):
    aliases = ("repoclosure",)
    summary = _("Display a list of unresolved dependencies for repositories")
    usage = "[--repoid <repoid>] [--pkg <pkg>]"

    def __init__(self, args):
        super(RepoClosureCommand, self).__init__(args)
        self.opts = None

    def configure(self, args):
        demands = self.cli.demands
        demands.sack_activation = True
        demands.available_repos = True
        self.opts = self._parse_args(args)
        if len(self.opts.repoid) > 0:
            for repo in self.base.repos.all():
                if repo.id not in self.opts.repoid:
                    repo.disable()
                else:
                    repo.enable()

    def run(self, args):
        unresolved = self._get_unresolved()
        for pkg in sorted(unresolved.keys()):
            print("package: {} from {}".format(str(pkg), pkg.reponame))
            print("  unresolved deps:")
            for dep in unresolved[pkg]:
                print("    {}".format(dep))

    def _get_unresolved(self):
        unresolved = {}

        resolved_deps = set()
        unresolved_deps = set()

        available = self.base.sack.query().available().filter(latest=True)
        if self.opts.pkglist:
            pkgs = set()
            for pkg in self.opts.pkglist:
                for pkgs_filtered in available.filter(name=pkg):
                    pkgs.add(pkgs_filtered)
        else:
            pkgs = available

        for pkg in pkgs:
            unresolved[pkg] = set()
            for req in pkg.requires:
                reqname = str(req)
                if reqname in resolved_deps:
                    continue
                if reqname in unresolved_deps:
                    unresolved[pkg].add(reqname)

                # XXX: https://bugzilla.redhat.com/show_bug.cgi?id=1186721
                if reqname.startswith("solvable:") or \
                        reqname.startswith("rpmlib("):
                    resolved_deps.add(reqname)
                    continue
                provider = available.filter(provides=reqname)
                if not provider:
                    unresolved[pkg].add(reqname)
                    unresolved_deps.add(reqname)
                else:
                    resolved_deps.add(reqname)
        return dict((k, v) for k, v in iter(unresolved.items()) if v)

    @staticmethod
    def _parse_args(args):
        alias = RepoClosureCommand.aliases[0]
        parser = dnfpluginsextras.ArgumentParser(alias)
        parser.add_argument("--repoid", default=[], action="append",
                            help=_("Specify repositories to use"))
        parser.add_argument("--pkg", default=[], action="append",
                            help=_("Check closure for this package only"),
                            dest="pkglist")
        return parser.parse_args(args)