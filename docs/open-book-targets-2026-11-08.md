The areas open to keyword remakes, measured: pets wins the demand and finance wins the supply

Bobby, 2026-11-08: "list easiest book targets that are easy keyword
phrases. remakes are searched by keywords. i think pets easy. what
areas of books at amazon open to this? finance nonfiction many areas"

MEASURED 2026-11-08 on Amazon's own books search (/s?k=<phrase>
&i=stripbooks), read in a browser session. Seventeen phrases, the
number is Amazon's reported result count, which is demand AND
competition at once.

THE ANSWER, IN ONE LINE: pets is the easiest to ENTER and the hardest
to WRITE, and finance/business is the opposite -- and the remake
openings are five specific phrases split across both.

THE MEASURED SET

  area      phrase                                results  top-1 price
  pets      rabbit shedding                             3     $16.50
  pets      rabbit nails trimming                       11     $11.99
  pets      rabbit hay                                  19     $0.00
  pets      how to stop your cat scratching              21     $0.00
  pets      rabbit potty training                       35     $14.99
  pets      rabbit diet                                133     $15.99
  pets      rabbit hutch                               169     $8.16
  pets      how to stop your dog barking               330     $13.99
  business  how to file taxes as a freelancer         254     $0.00
  business  how to price freelance work               260     $0.00
  business  how to negotiate salary                   558     $0.00
  finance   how to build a credit score               841     $19.99
  finance   how to budget for a wedding             1,000     $9.99
  finance   how to make a budget                    3,000     $5.99
  pets      rabbit breeds                          3,000     $10.21
  pets      dog training for dummies              2,000     $14.64
  selfhelp  how to build discipline              10,000     $19.97

WHY PETS IS EASY, AND IT IS STRUCTURAL RATHER THAN A MATTER OF TASTE:
a narrow animal and a narrow job is ONE phrase. "rabbit shedding" is
three books on earth; "rabbit nails trimming" is eleven. EIGHT of the
pets phrases measured sit under 500 results, and the six narrowest are
3, 11, 19, 21, 35 and 133. The finance and business phrases are 254,
260, 558, 841, 1,000 and 3,000 -- because "how to negotiate salary" is
a job that many books address and "rabbit shedding" is a problem only
one kind of book addresses.

AND BOBBY'S "REMAKES ARE SEARCHED BY KEYWORDS" IS MEASURABLE IN THE
TOP-1 FORMAT, WHICH IS THE PART THE COUNT ALONE MISSES. A remake is a
PRINT book. So the question is not "how many books hold this phrase"
but "does a PRINT book hold the top of it". MEASURED: FIVE of the
seventeen phrases have a top-1 price of $0.00, which is Amazon's own
display for a Kindle-only title -- and therefore NO PRINT BOOK HOLDS
THE TOP OF THOSE PHRASES.

  rabbit hay                            $0.00   <-- pets
  how to stop your cat scratching       $0.00   <-- pets
  how to file taxes as a freelancer     $0.00
  how to price freelance work           $0.00
  how to negotiate salary               $0.00

SO THE COUNT SAYS "PETS IS EASIEST AND FINANCE IS CROWDED" AND THE
FORMAT SAYS SOMETHING SHARPER: the pets phrases with a print
incumbent -- rabbit shedding, rabbit nails trimming, rabbit potty
training, rabbit diet, how to stop your dog barking -- need a real
book to beat, and the three finance/business ones do not, and neither
do the two Kindle-only pets ones. THE REMAKE OPENINGS ARE FIVE
SPECIFIC PHRASES, TWO IN PETS AND THREE IN FINANCE.

AND THE SUPPLY CHECK FLIPS THE ORDER, because a phrase is half the
answer and the other half is what we can write FROM. MEASURED on disk
2026-11-08:

  test-prep    148 files  119.5 MB   the deepest well: 234.9 MB of
                                      question banks, 224,490 questions
  business      64 files    2.5 MB   finance.php is 12,414 words,
                                      finance terms.txt 10,213 words,
                                      Domains-finance.txt 4,551 words
  medicine      48 files    1.3 MB   a different market
  psychology    35 files    1.5 MB
  pets           0 files    0.0 MB   **NO PET CORPUS AT ALL**

MEASURED: a walk of the whole Desktop for files mentioning rabbit,
hamster or guinea pig returned 8 files, and every one is an incidental
mention -- a movie-data CSV, a yellow-pages list, a biology MCQ bank.
The one usable piece is test-prep/testing/Biology-MCQ.csv (460,947
chars) carrying 89 mentions of fish, 64 of bird, 38 of dog, 26 of
sheep, 25 of rabbit, 11 of cat and 8 of horse -- which is 260 animal
facts and NOT a book.

SO PETS WINS THE DEMAND MEASUREMENT AND LOSES THE SUPPLY ONE. THE
FINANCE PHRASES WITH NO PRINT INCUMBENT SIT IN THE BUSINESS FOLDER WE
ALREADY HOLD 2.5 MB OF, AND THE DEMAND MEASUREMENT SAYS THOSE SAME
PHRASES HAVE A REAL BUYER AND FEW COMPETITORS.

THE RECOMMENDATION, AND IT IS THE ORDER THE MEASUREMENT PUTS THEM IN:
take "how to file taxes as a freelancer" (254), "how to price
freelance work" (260) and "how to negotiate salary" (558) -- three
print-free slots, and the supply to write them -- and then build the
pet corpus, because they are the easiest to sell and the furthest from
being written.

AND ONE THING TO KNOW BEFORE BUILDING ANY LIST: "rabbit hutch" (169)
puts A NOVEL at the top -- "The Rabbit Hutch: A Novel (National Book
Award...)". The longer phrase "how to build a rabbit hutch" (70)
excludes it. That is the catalogued 2026-10-31 failure repeating, and
it is why a phrase has to be specific enough to exclude what the buyer
did not ask for.

THE NUMBERS ARE STABLE, WHICH IS WHAT MAKES THEM A PLANNING INPUT.
MEASURED both dates on the six rabbit phrases both runs covered:

  rabbit hutch              179 -> 169   -6%
  rabbit diet               133 -> 133    0%
  rabbit potty training     33 ->  35   +6%
  rabbit nails trimming      11 ->  11    0%
  rabbit shedding            3 ->   3    0%
  rabbit hay                18 ->  19   +6%

A 6% band and no more. So a phrase measured open stays open.

THE INSTRUMENT'S LIMITS, and they are stated so a future session knows
what it is reading. Amazon's /s endpoint returns HTTP 503 to a plain
urllib request -- the 2026-10-31 finding, re-confirmed today -- so the
browser is the only instrument. The counts are from the SEARCH
endpoint; this machine's delivery country is Nepal, so the bestseller
grid returns "Sorry, there are no Best Sellers available in this
category" -- the search works and the grid does not. And Amazon
throttles rapid navigation: twelve back-to-back searches returned
"Sorry! Something went wrong!" on every one, so the measurement needs
one tab navigated slowly, and a fresh session name gets a fresh
daemon.

THE FILES
  catalog/open_book_targets_2026-11-08.json   the measured set, the
      drift check, the supply check and the ranking
  catalog/keyword_phrases.json                the catalogue, with
      today's numbers and five new finance rows
  tools/keyword_phrases.py                    the source, which is where
      the tool reads the measurements from -- MEASURED: updating the
      JSON alone changed nothing, because the tool never reads the JSON
  tests/test_keyword_phrases.py               three tests: the current
      measurement, the drift BOUND rather than one number, and the
      print-free slots
