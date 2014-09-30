HUNTDIR=./hun-tools
JAVA=/opt/sun-java/bin/java
NOOJJAR=nooj-cmd-1.0-with-Nooj-v3.1-20140421.jar
NOOJHOME=./NooJ
export PYTHONPATH = ./liblinear-1.91/python

# The following defaults should be overriden in the command line if need, eg. "make gettok SQLFILE=mystuff.sql OUTDIR=some/where/"
OUTDIR=../data/fb/comments.nlp
NOGS=POLITIKUSOK.nog,VALENCIA.nog,COMMUNION-AGENCY.nog,INDIVIDUALIZMUS.nog,OPTIMIZMUS_1.nog,OPTIMIZMUS_2.nog,ELSODLEGES_ERZEKELES.nog,ELSODLEGES_REGRESSZIO.nog,ELSODLEGES_DRIVE.nog,ELSODLEGES_IKAROSZ.nog,ELSODLEGES_VEDEKEZES.nog,MASODLAGOS_ABSZTRAKCIO.nog,MASODLAGOS_IDO.nog,MASODLAGOS_KORLATOZAS.nog,MASODLAGOS_TARSAS.nog,MASODLAGOS_ERKOLCS.nog,MASODLAGOS_INSTRUMENTALIS.nog,MASODLAGOS_REND.nog

# No. of parallel jobs to run
NCORES=6
# Name of tile with numbe of parallel jobs to run. May be modified while parallel is running, so num. of running jobs can be changed
PROCFILE=./.ncores


.PHONY: allnlp tokenize posmorph stem stem1 ner toxml nooj

all:

#allnlp: tokenize posmorph stem stem1 ner
allnlp: tokenize posmorph stem stem1 ner

# call huntoken (+ special tricks) to tokenize: *.txt => *.tok
tokenize:
	ls $(OUTDIR)/*.txt | parallel -j $(NCORES) --progress "echo {}; ./mytokenize.py {} {.}.tok"

# call hunpos + ocamorph on tokenized files 
# Do it in parallel processes to utilize all available CPU cores (but keep 1 core idle for other users :)
posmorph:
	ls $(OUTDIR)/*.tok | parallel -j $(NCORES) --progress "echo {}; $(HUNTDIR)/011.hunpos-hunmorph < {} > {.}.posmorph"

# Do stemming and morphana selection
# Use parallel
stem:
	ls $(OUTDIR)/*.posmorph | parallel -k -j $(NCORES) "echo {}; $(HUNTDIR)/012.stem -m --oovstr 'OOV' --morphdel '||' {} {.}.stem"

# Using .stem files disambiguate anas, improve lemmas
# Note: huntoken introduces some double blank lines, suppress these (cat -s) since they crash huntag (next step)
# TODO: merge this into stem
stem1:
	ls $(OUTDIR)/*.stem | parallel -k -j $(NCORES) "echo {}; ./chooseana.py {} | cat -s > {.}.stem1"

# Run NER on *.stem1 files, save into *.stem1.ner
# This uses NER code in /home/eszter/HunTag
ner:
	ls $(OUTDIR)/*.stem1 | parallel -j-2 "iconv -f UTF-8 -t CP1250//TRANSLIT < {} | python $(HUNTDIR)/HunTag/huntag.py tag -m $(HUNTDIR)/HunTag/models/ner.trendminer -b $(HUNTDIR)/HunTag/models/szeged.ner.all.bigram -c $(HUNTDIR)/HunTag/configs/hunner_trendminer.cfg > {}.ner.CP1250 ; grep -v '^Accuracy = ' {}.ner.CP1250 | iconv -f CP1250 -t UTF-8 > {}.ner ; rm {}.ner.CP1250"


# Convert *.ner files into XML in xml/*.xml
toxml:
	ls $(OUTDIR)/*.ner | parallel -j-2 "./tsv2noojxml.py {} > {}.xml 2>> tsv2noojxml.py.err"

# Run Java NooJ command line on xml files in $(OUTDIR) with grammars specified in $(NOGS)
# Move NooJ output files to $(OUTDIR)/nooj subdir
# -Xms256M -Xmx2048M
nooj:
	ls -1 $(OUTDIR)/*.xml | parallel -k -j $(PROCFILE) "$(JAVA) -jar $(NOOJHOME)/$(NOOJJAR) -w $(NOOJHOME) -i {} -l hu -x \<s\> -g $(NOGS)"

# For each NooJ output file (+ each NLP output XML file): parse them, save annotations+scores to database
getannotations:
	ls -1 $(OUTDIR)/*.xml.txt | parallel -v -k -j $(PROCFILE) "./annots.py {} {.} 2>> getannotations.err"
