#!/usr/bin/perl
use warnings;
use strict;
use feature qw/state signatures say multidimensional/;
use utf8;
use open qw(:std :encoding(UTF-8));

# after downloading you can run (assuming you don't really care about starting hour, here I set it to 19:00 UTC)
# ls mywellness*json | perl -nle '$d = (s/.*(\d\d\d\d-\d\d-\d\d).*/$1T19:00/r); print `python mywellness2tcx.py "$_" "$d"`'

# up to 3 workouts per day
my $workouts_per_day = 3;

die "use: get-all.pl <first activity number> <last activity number> <_mwappseu cookie value>" unless exists $ARGV[2];
die "invalid cookie format" unless $ARGV[2] =~ /^([0-9a-f-]+)\|([0-9a-zA-Z]+\.[0-9A-F]+)$/;
my $cookie = $ARGV[2];
my $token = $2;
my $mini = $ARGV[0];
my $maxi = $ARGV[1];

my $curl = qq{curl --silent --location --cookie "_mwappseu=$cookie"};

my $i = 0;
for my $i ($mini..$maxi)
{
    for my $pos (1..$workouts_per_day)
    {
        print "Checking: $i:$pos\r";
        my $posid = $pos + 1;
        my $hurl = "https://www.mywellness.com/cloud/Training/PerformedExerciseDetail/?idCr=$i&position=$posid&dayOpenSession=20240101&singleView=False";
        my $h = `$curl "$hurl"`;

        next unless $h =~ /window.physicalActivityAnalyticsId = '([^']+)'/;
        my $aaid = $1;

        next unless $h =~ /window.facilityId = '([^']+)'/;
        my $fid = $1;

        next unless $h =~ /API_APP_ID: "([^"]+)"/;
        my $apid = $1;

        my $logurl = "https://services.mywellness.com/Training/CardioLog/$aaid/Details?facilityId=$fid&_c=en-US&AppId=$apid&token=$token";
        my $log = `$curl "$logurl"`;

        next unless $log =~ m{"physicalActivityName":"([^"]+)"};
        my $n = $1;

        $log =~ m{"date":"(\d+)/(\d+)/(\d+)"};
        my $d = sprintf("%04d-%02d-%02d", $3, $1, $2);

        printf "%4d:%d $d ($n) aaid=$aaid fid=$fid apid=$apid\n", $i, $pos;

        my $fn = sprintf "mywellness-%05d_%d-%s.json", $i, $pos, $d;
        open(my $f, ">", $fn) or die $!;
        print $f $log;
    }
}