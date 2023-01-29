# Copyright (c) 2022 Amine Daoud.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import smtplib
import ssl
from email.message import EmailMessage
from email.mime.application import MIMEApplication


def send_email(subject, content, email, app_key, recipients, attachment_files):
    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    msg["From"] = email
    msg["To"] = recipients

    for file in attachment_files:
        with open(file, 'rb') as f:
            attach_file = MIMEApplication(f.read())
            attach_file.add_header('Content-Disposition',
                                   'attachment', filename=file)
            msg.add_attachment(attach_file)

    context = ssl.create_default_context()

    with smtplib.SMTP("smtp.gmail.com", port=587) as smtp:
        smtp.starttls(context=context)
        smtp.login(msg["From"], app_key)
        smtp.send_message(msg)
