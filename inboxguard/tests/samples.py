"""Raw email fixtures used across the test suite."""

PROMO = b"""From: Shoply Deals <deals@e.shoply.com>
To: me@example.com
Subject: FLASH SALE: 40% off everything - ends tonight!!
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <promo-1@shoply.com>
List-Unsubscribe: <https://shoply.com/u/abc>
Precedence: bulk
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

<html><body><img src="https://t.shoply.com/p.gif" width="1" height="1">
<h1>Shop now</h1><p>Use code SAVE40 for free shipping.</p>
<a href="https://shoply.com/1">Men</a><a href="https://shoply.com/2">Women</a>
<img src="a.jpg"><img src="b.jpg"><img src="c.jpg"><img src="d.jpg">
<p>You are receiving this email because you signed up. <a href="https://shoply.com/unsub">Unsubscribe</a></p>
</body></html>
"""

NEWSLETTER_ONLY_UNSUB = b"""From: Alice Writer <alice@blog.example.org>
To: me@example.com
Subject: Notes from this week
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <nl-1@blog.example.org>
List-Unsubscribe: <mailto:unsub@blog.example.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Hi all, this week I looked at three papers on parsing and wrote up what I learned.
You can unsubscribe at any time using the link below.
"""

PERSONAL = b"""From: Bob Friend <bob@example.net>
To: me@example.com
Subject: Lunch tomorrow?
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <p-1@example.net>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Hey, are you free for lunch tomorrow around 1? I found a new place near the station.
Let me know. Also, did you get the PDF I sent last week?
"""

TRANSACTIONAL = b"""From: Bank <noreply@bank.example.com>
To: me@example.com
Subject: Your verification code
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <t-1@bank.example.com>
List-Unsubscribe: <https://bank.example.com/u>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Your verification code is 482913. It expires in 10 minutes.
To stop these emails, unsubscribe in your account settings.
"""

AI_BOILERPLATE = b"""From: Sam Seller <sam@growthco.example>
To: me@example.com
Subject: Partnership opportunity
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <ai-1@growthco.example>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Certainly! Here is a polished email you can send. As an AI language model I can adapt the tone.

Dear [Recipient Name], I hope this email finds you well. I wanted to reach out about a partnership.
"""

AI_PLACEHOLDER = b"""From: Jo Outreach <jo@leadgen.example>
To: me@example.com
Subject: Quick question
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <ai-2@leadgen.example>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Hi there, I hope this email finds you well. I wanted to reach out because our robust, cutting-edge
platform can help you streamline your workflow and unlock the full potential of your team.
It is important to note that we leverage seamless integrations to foster growth.
Please feel free to reach out if you would like to delve into the details.

Best regards,
[Your Name]
"""

AI_STYLE_ONLY = b"""From: Chris Consultant <chris@advice.example>
To: me@example.com
Subject: Ideas for your team
Date: Mon, 09 Nov 2026 10:00:00 +0000
Message-ID: <ai-3@advice.example>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

I hope this email finds you well. In today's fast-paced world, it is important to note that teams
must navigate the complexities of change. Our holistic approach is a testament to meticulous planning.
Moreover, we leverage a robust and seamless process. Furthermore, we foster pivotal collaboration.
Additionally, we harness a plethora of tools to elevate outcomes for your organization.
"""
