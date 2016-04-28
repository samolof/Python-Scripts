#!/usr/bin/env python
# File Name: bibfiles_merge_tool.py
#
# Date Created: Apr 30,2012
#
# Last Modified:
#
# Author: sam
#
# Description: A tool for removing duplicate or similar entries from 
# a bunch of .bib files. Adjust SIMILARITY if too many false positives/negatives 	
#
##################################################################
import sys,re,os, os.path
import difflib,heapq
import optparse,glob
import tty,termios


#TMP=$(mktemp) && cat > $TMP && emacs $TMP; rm $TMP
#MK

FLASHMASTERBIB='flashMaster.bib'
TITLEONLY=None; DUPLICATESONLY=None
SOURCEFILES=[];MASTERFILE=None;OUTFILE=None
SIMILARITY=0.8

bibs=[]
possibilities=[]

bpat=re.compile(r"""(
	@(article|book|booklet|conference|inproceedings
		|conference|inbook|incollection|manual
		|masterthesis|misc|phdthesis|proceedings|techreport|unpublished)
	.*?)(?=@(article|book|booklet|conference|inproceedings
		|conference|inbook|incollection|manual
		|masterthesis|misc|phdthesis|proceedings|techreport|unpublished)|\s*\Z)
	""",re.S|re.I|re.X)

tpat=re.compile(r"""title(\s)*=(\s)*["|']?["|'|{](?P<tit>.*?)[}|"|']["|']?,""",re.S|re.I)
ppat=re.compile(r"""pages(\s)*=.*?(?P<pag>\d+).*?\s""",re.S|re.I)
ypat=re.compile(r"""year(\s)*=.*?(?P<yr>\d{4}).*?\s""",re.S|re.I)
vpat=re.compile(r"""volume(\s)*=.*?(?P<vol>\w+).*?\s""",re.S|re.I)
apat=re.compile(r"""author(\s)*=(\s)*["|']?[{](?P<auth>.*?)[}]["|']?,""",re.S|re.I)
typat=re.compile(r"""@(article|book|booklet|conference|inproceedings
			|conference|inbook|incollection|manual
			|masterthesis|misc|phdthesis|proceedings|techreport|unpublished)
		""",re.S|re.I|re.X)

jpat = re.compile(r"""journal(\s)*=(\s)*["|']?[{](?P<jour>.*?)[}]["|']?""",re.S|re.I)
bopat = re.compile(r"""booktitle(\s)*=(\s)*["|']?[{](?P<book>.*?)[}]["|']?""",re.S|re.I)
ipat = re.compile(r"""(institution|school)(\s)*=(\s)*["|']?[{](?P<inst>.*?)[}]["|']?""",re.S|re.I)



class Publication:
	def __init__(self,title,typ,tex=None, **kwargs):
		self.title=title
		self.tex=tex
		self.type=typ
		self.__dict__.update(kwargs)

	def similar(self,other,TITLEONLY=None):
		journalA='A'
		journalB='B'
		if self.journal and other.journal:
			journalA=re.sub('[\W]+','',self.journal).lower()
			journalB=re.sub('[\W]+','',other.journal).lower()

		if TITLEONLY != None:
			titlea = re.sub('[\W]+','',self.title).lower()
			titleb = re.sub('[\W]+','',other.title).lower()
	
	
			return (titlea == titleb) 


		if self.volume and other.volume :
			if self.page and other.page:
				return (self.volume == other.volume) \
					and (self.page == other.page) 

			elif self.year and other.year:
				return (journalA == journalB)\
					and (self.volume == other.volume)\
					and (self.year == other.year) 

		if self.booktitle and other.booktitle:
				return (self.booktitle == other.booktitle)\
					and (self.type== other.type)

		if self.institution and other.institution and 'thesis' in self.type:
				return (self.type == other.type)\
					and (self.institution == other.institution)
								
		
		if self.page and self.year and other.page and other.year:
			return (journalA == journalB)\
				and (self.page == other.page)\
				and (self.year == other.year) 

		return False

def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


def cfy(text,c1=37,c2=45):
	return "\033[%s;%sm%s\033[m" % (c1,c2,text)


def display(source, master, sourcename, mastername,count_str):
	os.system('clear')
	
	print """A: \033[0;35m%s\033[m
%s
-------------------------------------------------------------
B: \033[0;35m%s\033[m
%s
""" % (mastername, master.tex, sourcename,source.tex) 
	print "=" * min(100,len(master.title))
	print "%s\n%s\n%s(%s)\n" % (cfy(count_str,0,31),source.title,"",cfy(master.title,0,31))
	print "=" * len(master.title)
	print "%s, %s, %s, %s, %s, %s" %( cfy("(d)") + "uplicate (don't add to results)",
				 cfy("(s)")+ "kip/not duplicate",
				 cfy("(S)")+ "kip all (will add all to results)",
				 cfy("(R)")+ "eplace (use new entry in place of similar one in master)",
				 cfy("(w)") + "rite and quit", 
				 cfy("(q)") + "uit:"),

	while 1:
		response = getch()
		reponse = response.lower()
		if reponse == 'd' or reponse == 's' or reponse == 'w' or \
		     reponse == 'r' or reponse == 'q':
			break

	return response


def get_close_matches(pub, poss, n=6, cutoff=0.85):


	result=[]
	s=difflib.SequenceMatcher()
	s.set_seq2(pub.title)
	
	for x in poss:
		s.set_seq1(x.title)
		if s.real_quick_ratio() >= cutoff and s.quick_ratio() >= cutoff \
		     and s.ratio() >= cutoff:
			result.append((s.ratio(),x))
	
	

	result = heapq.nlargest(n,result)
	return [x for score,x in result]


def preprocess(doc):
	records = re.finditer(bpat,doc)
	
	publications=[]

	for r in records:
		r=r.group(1)
		title=re.search(tpat,r)
		if title:
			title= title.group('tit')
		else:
			continue
		title=title.replace('\n','').replace('\t','').strip()
		ptype=re.search(typat,r).group(1).lower()

		page=re.search(ppat,r)
		if page : page = page.group('pag')
		
		year=re.search(ypat,r)
		if year : year= year.group('yr')
		
		volume=re.search(vpat,r)
		if volume : volume = volume.group('vol')
		
		author=re.search(apat,r)
		if author : author = author.group('auth')

		institution=re.search(ipat,r)
		if institution: institution=institution.group('inst').lower()

		book=re.search(bopat,r)
		if book: book=book.group('book').lower()
		
		journal=re.search(jpat,r)
		if journal: journal=journal.group('jour').lower()

		r=r.rstrip('\n')
		publications.append(Publication(title=title,typ=ptype,tex=r,journal=journal,\
					page=page,year=year,\
					booktitle=book,institution=institution,\
					volume=volume,author=author))

	return publications




def main():

	output=[]
	
	counter=0
	totalCount=len(candidates)
		
	for candidate in candidates:
		counter += 1
		count_str = "%d/%d" % (counter, totalCount)
		similar_titles = get_close_matches(candidate, possibilities)


		for s in similar_titles:
		

			if candidate.similar(s,TITLEONLY) :
				resp='d'
			else:
				resp= display(candidate, s, sourcename, mastername, count_str)

			if resp == 'q':
				return None
			elif resp == 'w':
				return output
			elif resp == 'd':
				if DUPLICATESONLY:
					output.append(candidate.tex)
				break
			elif resp == 'R':
				s.tex = candidate.tex
				break
			elif resp == 's':
				continue	
			elif resp == 'S':
				possibilities.append(candidate)
				output.append(candidate.tex)
				for rc in candidates[counter:]:
					output.append(rc.tex)
					return output
		else:
			possibilities.append(candidate)  
			if not DUPLICATESONLY:
				output.append(candidate.tex)
				
	return output




if __name__=="__main__":
	usage="usage: %prog [options] <source.bib> [master.bib]"
	parser=optparse.OptionParser(usage)
	parser.add_option("-o", "--output", type="string",
			help="""specify an output bib file. Output is sent to stdout by default"""
			,dest="outfile",action="store")

	parser.add_option("-s" , type="float", action="store", dest="similarity",
		default= 0.75, 
		help="Define a similarity index for checking duplicates. Values range is [0,1] with 1 being an exact match" 
		     "[default: %default]")

	parser.add_option("-t" , action="store_true", dest="titleonly", help="Use only publication titles to check for duplicates")
	parser.add_option("-v" , action="store_true",  dest="duplicatesonly", help="Output only duplicate publications")

	parser.add_option("-m" , action="store_true", dest="sourceonly", 
			help="Don't merge, output only non-duplicates")

	(options,args)= parser.parse_args()
	TITLEONLY=options.titleonly
	DUPLICATESONLY=options.duplicatesonly
	SOURCEONLY=options.sourceonly
	OUTFILE=options.outfile
	SIMILARITY=options.similarity

	if len(args) < 1:
		parser.error("Must specify at least one bib file to merge")
	else:
		for i in range(len(args)-1):
			sfs = args[i]

			for sf in glob.glob(sfs): 

				if not os.path.isfile(sf):
					print "%s does not exist" % sf
					continue

				SOURCEFILES.append(sf)


	if len(args) < 2: 
		if not os.path.isfile(FLASHMASTERBIB):
			parser.error("Couldn't find flashMaster.bib in the current path. Specify the path to a master .bib file in the command line args")
		else:
			MASTERFILE=FLASHMASTERBIB
	else:
		MASTERFILE=args[len(args) -1 ]
		if not os.path.isfile(MASTERFILE) :
			print "%s is not an existing file" % MASTERFILE
			os._exit(1)
		print "Using %s as MASTER: " % MASTERFILE

	master=open(MASTERFILE,'r'); mastertext= master.read()
	mastername=master.name
	possibilities = preprocess(mastertext)


	out=OUTFILE and open(OUTFILE,'w') or sys.stdout

	for SOURCEFILE in SOURCEFILES:
		source=open(SOURCEFILE,'r') ; sourcetext = source.read()

		candidates  =   preprocess(sourcetext)

		print 'Processing %s' % SOURCEFILE

		sourcename=source.name
		res= main()
		if res:
			bibs.extend(res)
		source.close()

	

	if bibs is not None or bibs != []:
		#write contents of master bib file to stdout if user does not specify otherwise
		if not SOURCEONLY and not DUPLICATESONLY:
			for p in possibilities:
				out.write(p.tex + "\n\n")
		else:
			for bibtexentry in bibs:
				out.write(bibtexentry + "\n")


	master.close()
	if OUTFILE: out.close()
