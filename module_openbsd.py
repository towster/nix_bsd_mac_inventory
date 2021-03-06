import paramiko


class GetBSDData:
    def __init__(self, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                 get_serial_info, get_hardware_info, get_os_details,
                 get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug):

        self.machine_name = ip
        self.port = int(ssh_port)
        self.timeout = timeout
        self.username = usr
        self.password = pwd
        self.ssh = paramiko.SSHClient()
        self.use_key_file = use_key_file
        self.key_file = key_file
        self.get_serial_info = get_serial_info
        self.get_hardware_info = get_hardware_info
        self.get_os_details = get_os_details
        self.get_cpu_info = get_cpu_info
        self.get_memory_info = get_memory_info
        self.ignore_domain = ignore_domain
        self.upload_ipv6 = upload_ipv6
        self.debug = debug
        self.ssh = paramiko.SSHClient()
        self.conn = None
        self.device_name = None
        self.sysdata = {}
        self.alldata = []

        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def main(self):
        self.connect()
        self.get_sys()
        self.get_CPU()
        self.get_RAM()
        self.alldata.append(self.sysdata)
        self.get_IP()
        return self.alldata

    def connect(self):
        try:
            if not self.use_key_file:
                self.ssh.connect(str(self.machine_name), port=self.port, username=self.username, password=self.password,
                                 timeout=self.timeout)
            else:
                self.ssh.connect(str(self.machine_name), port=self.port, username=self.username,
                                 key_filename=self.key_file, timeout=self.timeout)
        except paramiko.AuthenticationException:
            print str(self.machine_name) + ': authentication failed'
            return None
        except Exception as err:
            print str(self.machine_name) + ': ' + str(err)
            return None

    def get_CPU(self):
        if self.get_cpu_info:
            stdin, stdout, stderr = self.ssh.exec_command(
                "sysctl -n hw.model; sysctl -n hw.ncpu;  sysctl -n hw.cpuspeed")
            data_out = stdout.readlines()
            data_err = stderr.readlines()
            if not data_err:
                cpumodel = data_out[0].strip()
                cpucount = data_out[1].strip()
                cpuspeed = data_out[2].strip()
                self.sysdata.update({'cpumodel': cpumodel})
                self.sysdata.update({'cpucount': cpucount})
                self.sysdata.update({'cpuspeed': cpuspeed})

            else:
                print data_err

    def get_RAM(self):
        if self.get_memory_info:
            stdin, stdout, stderr = self.ssh.exec_command("sysctl -n hw.physmem")
            data_out = stdout.readlines()
            data_err = stderr.readlines()
            if not data_err:
                memory = int(data_out[0].strip()) / 1024 / 1024
                self.sysdata.update({'memory': memory})
            else:
                print 'Error: ', data_err

    def get_name(self):
        stdin, stdout, stderr = self.ssh.exec_command("/bin/hostname")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            full_name = data_out[0].strip()
            if self.ignore_domain:
                if '.' in full_name:
                    return full_name.split('.')[0]
                else:
                    return full_name
            else:
                return full_name
        else:
            print 'Error: ', data_err

    def get_IP(self):
        stdin, stdout, stderr = self.ssh.exec_command("ifconfig")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            nics = []
            tmpv4 = {}
            tmpv6 = {}
            macs = {}

            for rec in data_out:
                if 'flags=' in rec:
                    device = rec.split(':')[0]
                    if tmpv4 == {}:
                        tmpv4.update({'device': self.device_name})
                        tmpv4.update({'tag': device})
                    else:
                        nics.append(tmpv4)
                        tmpv4 = {}
                        tmpv4.update({'device': self.device_name})
                        tmpv4.update({'tag': device})
                    if tmpv6 == {}:
                        tmpv6.update({'device': self.device_name})
                        tmpv6.update({'tag': device})
                    else:
                        nics.append(tmpv6)
                        tmpv6 = {}
                        tmpv6.update({'device': self.device_name})
                        tmpv6.update({'tag': device})
                    if macs != {}:
                        nics.append(macs)
                        macs = {}
                    macs.update({'device': self.device_name})
                    macs.update({'port_name': device})
                else:
                    if rec.strip().startswith('lladdr'):
                        mac = rec.split()[1].strip()
                        tmpv4.update({'macaddress': mac})
                        tmpv6.update({'macaddress': mac})
                        macs.update({'macaddress': mac})
                    if rec.strip().startswith('inet '):
                        ipv4 = rec.split()[1]
                        tmpv4.update({'ipaddress': ipv4})
                    if rec.strip().startswith('inet6'):
                        ipv6 = rec.split()[1]
                        if '%' in ipv6:
                            ipv6 = ipv6.split('%')[0]
                        tmpv6.update({'ipaddress': ipv6})

            nics.append(tmpv4)
            nics.append(tmpv6)
            nics.append(macs)

            for nic in nics:
                if 'tag' in nic:
                    if nic['tag'].startswith('lo'):
                        pass
                    else:
                        if 'ipaddress' in nic or 'macaddress' in nic:
                            self.alldata.append(nic)
                elif 'port_name' in nic:
                    if nic['port_name'].startswith('lo'):
                        pass
                    else:
                        if 'ipaddress' in nic or 'macaddress' in nic:
                            self.alldata.append(nic)
        else:
            print 'Error: ', data_err

    def get_sys(self):
        self.device_name = self.get_name()
        stdin, stdout, stderr = self.ssh.exec_command("uname -rsv")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            data = ' '.join(data_out).split()
            os = data[0].strip()
            self.sysdata.update({'os': os})
            version = data[1].strip()
            self.sysdata.update({'osver': version})
            kernel_version = data[2].strip()
            self.sysdata.update({'osverno': kernel_version})
            self.sysdata.update({'name': self.device_name})

        else:
            print 'Error: ', data_err

        stdin, stdout, stderr = self.ssh.exec_command("sysctl -n hw.product; sysctl -n hw.vendor ; sysctl -n hw.uuid")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            vendor = data_out[0].strip()
            uuid = data_out[2].strip()
            self.sysdata.update({'uuid': uuid})
            mft = data_out[1].strip()
            if mft.lower().strip() in ['vmware, inc.', 'bochs', 'kvm', 'qemu', 'microsoft corporation', 'xen',
                                       'innotek gmbh']:
                manufacturer = 'virtual'
                self.sysdata.update({'type': manufacturer})
            else:
                self.sysdata.update({'type': 'physical'})
            self.sysdata.update({'manufacturer': vendor})

        else:
            print 'Error: ', data_err
