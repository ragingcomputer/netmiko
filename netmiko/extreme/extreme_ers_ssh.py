"""Netmiko support for Extreme Ethernet Routing Switch."""
import time
import re
from netmiko.cisco_base_connection import CiscoSSHConnection
from netmiko.ssh_exception import NetmikoAuthenticationException

# Extreme ERS presents Enter Ctrl-Y to begin.
CTRL_Y = "\x19"


class ExtremeErsBase(CiscoSSHConnection):
    """Netmiko support for Extreme Ethernet Routing Switch."""

    def save_config(self, cmd="save config", confirm=False, confirm_response=""):
        """Save Config"""
        return super().save_config(
            cmd=cmd, confirm=confirm, confirm_response=confirm_response
        )


class ExtremeErsSSH(ExtremeErsBase):
    """Netmiko support for SSH connection to Extreme Ethernet Routing Switch."""

    def special_login_handler(self, delay_factor=1):
        """
        Extreme ERS presents the following as part of the login process:

        Enter Ctrl-Y to begin.
        """
        delay_factor = self.select_delay_factor(delay_factor)

        # Handle 'Enter Ctrl-Y to begin'
        output = ""
        i = 0
        while i <= 12:
            output = self.read_channel()
            if output:
                if "Ctrl-Y" in output:
                    self.write_channel(CTRL_Y)
                if "sername" in output:
                    self.write_channel(self.username + self.RETURN)
                elif "ssword" in output:
                    self.write_channel(self.password + self.RETURN)
                    break
                time.sleep(0.5 * delay_factor)
            else:
                self.write_channel(self.RETURN)
                time.sleep(1 * delay_factor)
            i += 1


class ExtremeErsTelnet(ExtremeErsBase):
    """Netmiko support for Telnet connection to Extreme Ethernet Routing Switch."""

    def telnet_login(
        self,
        pri_prompt_terminator=r"#\s*$",
        alt_prompt_terminator=r">\s*$",
        username_pattern=r"[Ee]nter\s*[Uu]sername",
        pwd_pattern=r"[Ee]nter\s*[Pp]assword",
        delay_factor=1,
        max_loops=20,
    ):
        """Extreme ERS presents the following as part of the login process:
        Enter Ctrl-Y to begin.
        Telnet login. Can be username/password or just password.
        Some devices have a menu on login. Need to press C to get
        a command prompt
        """

        delay_factor = self.select_delay_factor(delay_factor)
        time.sleep(1 * delay_factor)

        output = ""
        return_msg = ""
        sent_user = False
        sent_pass = False
        i = 1
        while i <= max_loops:
            try:
                output = self.read_channel()
                return_msg += output

                # Case matches exactly in every firmware tested for
                # ERS 5510 & 5520 v4 thru latest
                if "Ctrl-Y" in output:
                    self.write_channel(b"\x19\n")

                # in case terminal is configured to bring up menu first
                # press c to enter command prompt
                if "Use arrow keys to highlight option" in output:
                    self.write_channel(b"c\n")

                # Search for username pattern / send username
                if re.search(username_pattern, output, flags=re.I) and not sent_user:
                    sent_user = True
                    self.write_channel(b"\x09")
                    time.sleep(0.1 * delay_factor)
                    self.write_channel(self.username + self.TELNET_RETURN)
                    time.sleep(1 * delay_factor)

                # Search for password pattern / send password
                if re.search(pwd_pattern, output, flags=re.I) and not sent_pass:
                    sent_pass = True
                    self.write_channel(self.password + self.TELNET_RETURN)
                    time.sleep(0.5 * delay_factor)

                # Check if proper data received
                if re.search(pri_prompt_terminator, output, flags=re.M) or re.search(
                    alt_prompt_terminator, output, flags=re.M
                ):
                    return return_msg

                # self.write_channel(self.TELNET_RETURN)
                time.sleep(0.5 * delay_factor)
                i += 1
            except EOFError:
                self.remote_conn.close()
                msg = f"Login failed: {self.host}"
                raise NetmikoAuthenticationException(msg)

        # Last try to see if we already logged in
        self.write_channel(self.TELNET_RETURN)
        time.sleep(0.5 * delay_factor)
        output = self.read_channel()
        return_msg += output
        if re.search(pri_prompt_terminator, output, flags=re.M) or re.search(
            alt_prompt_terminator, output, flags=re.M
        ):
            return return_msg

        self.remote_conn.close()
        msg = f"Login failed: {self.host}"
        raise NetmikoAuthenticationException(msg)
