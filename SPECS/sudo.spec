# comment out if no extra version
%global extraver p5

Summary: Allows restricted root access for specified users
Name: sudo
Version: 1.9.15
# %autoselect cannot be used in Z-stream releases
# The .2 after %{?dist} must be increased in the next Z-stream release
Release: 8.%{?extraver}%{?dist}.2
License: ISC
URL: https://www.sudo.ws
Source0: %{url}/dist/%{name}-%{version}%{?extraver}.tar.gz
Source1: sudoers
Source2: sudo-ldap.conf
Requires: pam
Recommends: system-default-editor
Recommends: %{name}-python-plugin%{?_isa} = %{version}-%{release}

BuildRequires: make
BuildRequires: pam-devel
BuildRequires: groff
BuildRequires: openldap-devel
BuildRequires: flex
BuildRequires: bison
BuildRequires: libtool
BuildRequires: audit-libs-devel libcap-devel
BuildRequires: libselinux-devel
BuildRequires: systemd-rpm-macros
BuildRequires: gettext
BuildRequires: zlib-devel


Patch1: coverity.patch
Patch2: sudo-conf.patch
Patch3: cve-2025-32462.patch
Patch4: cve-2025-32463.patch

%description
Sudo (superuser do) allows a system administrator to give certain
users (or groups of users) the ability to run some (or all) commands
as root while logging all commands and arguments. Sudo operates on a
per-command basis.  It is not a replacement for the shell.  Features
include: the ability to restrict what commands a user may run on a
per-host basis, copious logging of each command (providing a clear
audit trail of who did what), a configurable timeout of the sudo
command, and the ability to use the same configuration file (sudoers)
on many different machines.

%package        devel
Summary:        Development files for %{name}
Requires:       %{name} = %{version}-%{release}

%description    devel
The %{name}-devel package contains header files developing sudo
plugins that use %{name}.

%package        python-plugin
Summary:        Python plugin for %{name}
Requires:       %{name} = %{version}-%{release}
BuildRequires:  python3-devel


%description    python-plugin
%{name}-python-plugin allows using sudo plugins written in Python.

%prep
%autosetup -p1 -n %{name}-%{version}%{?extraver}

%build
# Remove bundled copy of zlib
rm -rf zlib/

%ifarch s390 s390x sparc64
F_PIE=-fPIE
%else
F_PIE=-fpie
%endif

export CFLAGS="$RPM_OPT_FLAGS $F_PIE" LDFLAGS="-pie -Wl,-z,relro -Wl,-z,now"


%configure \
        --prefix=%{_prefix} \
        --sbindir=%{_sbindir} \
        --libdir=%{_libdir} \
        --docdir=%{_pkgdocdir} \
        --enable-tmpfiles.d=%{_tmpfilesdir} \
        --disable-openssl \
        --disable-root-mailer \
        --enable-intercept \
        --disable-log-server \
        --disable-log-client \
        --with-logging=syslog \
        --with-logfac=authpriv \
        --with-pam \
        --with-pam-login \
        --with-editor=/usr/bin/vi \
        --with-env-editor \
        --with-ignore-dot \
        --with-tty-tickets \
        --with-ldap \
        --with-ldap-conf-file="%{_sysconfdir}/sudo-ldap.conf" \
        --with-selinux \
        --with-sendmail=/usr/sbin/sendmail \
        --with-passprompt="[sudo] password for %p: " \
        --enable-python \
        --enable-zlib=system \
        --with-linux-audit \
        --with-sssd

make

%check
make check

%install
rm -rf $RPM_BUILD_ROOT

# Update README.LDAP (#736653)
sed -i 's|/etc/ldap\.conf|%{_sysconfdir}/sudo-ldap.conf|g' README.LDAP.md

make install DESTDIR="$RPM_BUILD_ROOT" install_uid=`id -u` install_gid=`id -g` sudoers_uid=`id -u` sudoers_gid=`id -g`

chmod 755 $RPM_BUILD_ROOT%{_bindir}/* $RPM_BUILD_ROOT%{_sbindir}/*
install -p -d -m 700 $RPM_BUILD_ROOT/var/db/sudo
install -p -d -m 700 $RPM_BUILD_ROOT/var/db/sudo/lectured
install -p -d -m 750 $RPM_BUILD_ROOT/etc/sudoers.d
install -p -c -m 0440 %{SOURCE1} $RPM_BUILD_ROOT/etc/sudoers
install -p -c -m 0640 %{SOURCE2} $RPM_BUILD_ROOT/%{_sysconfdir}/sudo-ldap.conf

# create sudo-ldap.conf man
echo ".so man5/sudoers.ldap.5" > sudo-ldap.conf.5
gzip sudo-ldap.conf.5
install -p -c -m 0644 sudo-ldap.conf.5.gz $RPM_BUILD_ROOT/%{_mandir}/man5/sudo-ldap.conf.5.gz
rm -f sudo-ldap.conf.5.gz

# we are not building sendlog so we don't need this
rm -rf $RPM_BUILD_ROOT/%{_mandir}/man8/sudo_sendlog.8

#add sudo to protected packages
install -p -d -m 755 $RPM_BUILD_ROOT/etc/dnf/protected.d/
touch sudo.conf
echo sudo > sudo.conf
install -p -c -m 0644 sudo.conf $RPM_BUILD_ROOT/etc/dnf/protected.d/
rm -f sudo.conf

chmod +x $RPM_BUILD_ROOT%{_libexecdir}/sudo/*.so # for stripping, reset in %%files

# Remove examples; Examples can be found in man pages too.
rm -rf $RPM_BUILD_ROOT%{_datadir}/examples/sudo

#Remove all .la files
find $RPM_BUILD_ROOT -name '*.la' -exec rm -f {} ';'

# Remove sudoers.dist
rm -f $RPM_BUILD_ROOT%{_sysconfdir}/sudoers.dist

%find_lang sudo
%find_lang sudoers

cat sudo.lang sudoers.lang > sudo_all.lang
rm sudo.lang sudoers.lang

mkdir -p $RPM_BUILD_ROOT/etc/pam.d

cat > $RPM_BUILD_ROOT/etc/pam.d/sudo << EOF
#%%PAM-1.0
auth       include      system-auth
account    include      system-auth
password   include      system-auth
session    include      system-auth
EOF

cat > $RPM_BUILD_ROOT/etc/pam.d/sudo-i << EOF
#%%PAM-1.0
auth       include      sudo
account    include      sudo
password   include      sudo
session    optional     pam_keyinit.so force revoke
session    include      sudo
EOF

%files -f sudo_all.lang
%defattr(-,root,root)
%attr(0440,root,root) %config(noreplace) /etc/sudoers
%attr(0640,root,root) %config(noreplace) /etc/sudo.conf
%attr(0640,root,root) %config(noreplace) %{_sysconfdir}/sudo-ldap.conf
%attr(0750,root,root) %dir /etc/sudoers.d/
%config(noreplace) /etc/pam.d/sudo
%config(noreplace) /etc/pam.d/sudo-i
%attr(0644,root,root) %{_tmpfilesdir}/sudo.conf
%attr(0644,root,root) %config(noreplace) /etc/dnf/protected.d/sudo.conf
%dir /var/db/sudo
%dir /var/db/sudo/lectured
%attr(4111,root,root) %{_bindir}/sudo
%{_bindir}/sudoedit
%{_bindir}/cvtsudoers
%attr(0111,root,root) %{_bindir}/sudoreplay
%attr(0755,root,root) %{_sbindir}/visudo
%dir %{_libexecdir}/sudo
%attr(0755,root,root) %{_libexecdir}/sudo/sesh
%attr(0644,root,root) %{_libexecdir}/sudo/sudo_noexec.so
%attr(0644,root,root) %{_libexecdir}/sudo/audit_json.so
%attr(0644,root,root) %{_libexecdir}/sudo/sudoers.so
%attr(0644,root,root) %{_libexecdir}/sudo/group_file.so
%attr(0644,root,root) %{_libexecdir}/sudo/system_group.so
%attr(0644,root,root) %{_libexecdir}/sudo/sudo_intercept.so
%attr(0644,root,root) %{_libexecdir}/sudo/libsudo_util.so.?.?.?
%{_libexecdir}/sudo/libsudo_util.so.?
%{_libexecdir}/sudo/libsudo_util.so
%{_mandir}/man5/sudoers.5*
%{_mandir}/man5/sudoers.ldap.5*
%{_mandir}/man5/sudo-ldap.conf.5*
%{_mandir}/man5/sudo.conf.5*
%{_mandir}/man8/sudo.8*
%{_mandir}/man8/sudoedit.8*
%{_mandir}/man8/sudoreplay.8*
%{_mandir}/man8/visudo.8*
%{_mandir}/man1/cvtsudoers.1*
%{_mandir}/man5/sudoers_timestamp.5*
%dir %{_pkgdocdir}/
%{_pkgdocdir}/*
%{!?_licensedir:%global license %%doc}
%license LICENSE.md
%exclude %{_pkgdocdir}/ChangeLog


%files devel
%doc plugins/sample/sample_plugin.c
%{_includedir}/sudo_plugin.h
%{_mandir}/man5/sudo_plugin.5*

%files python-plugin
%{_mandir}/man5/sudo_plugin_python.5.gz
%attr(0644,root,root) %{_libexecdir}/sudo/python_plugin.so

%changelog
* Wed Jul 09 2025 Alejandro López <allopez@redhat.com> - 1.9.15-8.p5.2
- RHEL 10.0.Z ERRATUM
- CVE-2025-32462 sudo: LPE via host option Resolves: RHEL-100008
- CVE-2025-32463 sudo: LPE via chroot option Resolves: RHEL-100021

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 1.9.15-8.p5
- Bump release for October 2024 mass rebuild:

* Wed Aug 21 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-7.p5
- RHEL 10.0 ERRATUM
- sudo-1.9.15-2.p5.el10: RHEL SAST Automation: address 4 High impact true
  positive(s) Resolves: RHEL-44436
- sudo subpackage sudo-logsrvd should not be built Resolves: RHEL-52864

* Mon Aug 19 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-6.p5
- RHEL 10.0 ERRATUM
- sudo-1.9.15-2.p5.el10: RHEL SAST Automation: address 4 High impact true
  positive(s) Resolves: RHEL-44436
- sudo subpackage sudo-logsrvd should not be built Resolves: RHEL-52864

* Mon Aug 19 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-5.p5
- RHEL 10.0 ERRATUM
- sudo-1.9.15-2.p5.el10: RHEL SAST Automation: address 4 High impact true
  positive(s) Resolves: RHEL-44436
- sudo subpackage sudo-logsrvd should not be built Resolves: RHEL-52864

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 1.9.15-4.p5
- Bump release for June 2024 mass rebuild

* Tue May 28 2024 koncpa <pkoncity@redhat.com> - 1.9.15-3.p5
- Enable RHEL gating for sudo

* Thu Feb 08 2024 Yaakov Selkowitz <yselkowi@redhat.com> - 1.9.15-2.p5
- Avoid sendmail build dependency

* Wed Jan 24 2024 Radovan Sroka <rsroka@redhat.com> - 1.9.15-1.p5
- Rabase to 1.9.15p5
- sudo-1_9_15p5 is available Resolves: rhbz#2248505
- TRIAGE CVE-2023-42465 sudo: Targeted Corruption of Register and Stack
  Variables Resolves: rhbz#2255569

* Tue Jul 25 2023 Yaakov Selkowitz <yselkowi@redhat.com> - 1.9.14-1.p3
- Rebase to 1.9.14p3
- sudo-1_9_14p2 is available Resolves: rhbz#2175672
- sudo fails to build with Python 3.12: FAILED: testcase
  check_example_group_plugin_is_able_to_debug() Resolves: rhbz#2186412

* Sat Jul 22 2023 Fedora Release Engineering <releng@fedoraproject.org> - 1.9.13-6.p2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_39_Mass_Rebuild

