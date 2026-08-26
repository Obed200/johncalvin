from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Profile
from news.models import Article

User = get_user_model()

ARTICLES = [
    ("Central Banks Signal a Slower Path on Rates",
     "Policymakers in three major economies hint at patience, favoring data over drama as inflation cools unevenly.",
     "Economy",
     "Officials speaking this week converged on a common theme: no rush. After eighteen months of aggressive tightening, the tone from monetary authorities has shifted from urgency to observation.\n\nMarket pricing had assumed a faster pivot, but futures adjusted quickly once [the latest statement](https://example.com/statement) landed.",
     True),
    ("The Founders Who Walked Away From Their Own Unicorns",
     "A growing number of company builders are choosing to step back at the peak, trading control for a different kind of freedom.",
     "Blogs",
     "Succession has always been the hardest chapter for a founder to write. Increasingly, some are choosing to write it early.\n\nThe move runs against instinct, but those who have done it describe a common thread: clarity about what they are actually good at.",
     False),
    ("Inside the Quiet Race to Rebuild the Power Grid",
     "Utilities are spending at levels unseen in a generation, betting that electrification will outpace every forecast.",
     "Technology",
     "The grid was built for a world of predictable, one-directional power flow. That world is gone.\n\nUtilities that spent decades optimizing for stability are now being asked to optimize for growth. Our reporter walks through one substation rebuild:\n\n[How a substation is rebuilt](https://www.youtube.com/watch?v=dQw4w9WgXcQ)\n\nThe full spending plan is published at https://example.com/grid-plan for anyone who wants the numbers.",
     False),
    ("Wetlands Return to a River That Was Paved Over",
     "A decade-long restoration is bringing back water, birds and a very different flood map.",
     "Environment",
     "Where a culvert once carried the river beneath a car park, there is now open water.\n\nEcologists tracking the site say species counts have roughly tripled since the channel was reopened.",
     False),
    ("Schools Are Rewriting the Timetable Around Attention",
     "Later starts, shorter blocks and fewer subjects a day — early results from a national trial are in.",
     "Education",
     "The change sounds administrative and turns out not to be. Teachers describe classrooms that simply behave differently after lunch.\n\nThe trial's interim report is available at https://example.com/timetable-trial.",
     False),
    ("A Title Race Decided in the Final Ninety Seconds",
     "Two clubs, one point apart, and a finish that will be replayed for a decade.",
     "Sports",
     "It had been a season of narrow margins, so it was fitting that it ended on one.\n\nThe winning move started, as these things often do, with a defender refusing to clear the ball.",
     False),
    ("What's New on The Ledger This Week",
     "Photo galleries, embedded video and clickable story cards — a short note on what changed.",
     "Updates",
     "Stories can now carry as many photos as they need, with one chosen as the spotlight image for the front page.\n\nAuthors can drop links straight into a sentence, and a YouTube address on its own line plays right on the page.",
     False),
]


class Command(BaseCommand):
    help = "Seeds a demo administrator, a demo author and a handful of sample stories."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin", defaults={"first_name": "Site Administrator", "is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password("admin12345")
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created administrator "admin" / password "admin12345"'))

        author, created = User.objects.get_or_create(
            username="jkim", defaults={"first_name": "Jordan Kim"}
        )
        if created:
            author.set_password("author12345")
            author.save()
            Profile.objects.filter(user=author).update(role="author", bio="Covers markets and monetary policy.")
            self.stdout.write(self.style.SUCCESS('Created author "jkim" / password "author12345"'))

        for title, dek, category, body, featured in ARTICLES:
            Article.objects.get_or_create(
                title=title,
                defaults={"dek": dek, "category": category, "body": body, "author": admin, "featured": featured},
            )
        self.stdout.write(self.style.SUCCESS("Demo content seeded."))
