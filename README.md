Utilities for LIFT (Lexicon Interchange Format). [Lift](https://code.google.com/archive/p/lift-standard/) is a XML vocabulary for representing lexicon in project of language description. It is used by SIL Flex and Elan associated with tools for the interlinearisation of texts.

# Installation


```python
pip install git+https://github.com/sylvainloiseau/pylift.git#egg=pylift
```



# Usage

The package install a ```liftlex``` command at the command line.

## Print summary of a lexicon


```console
$ liftlex summary tests/data/FlexLiftExport.lift
182 entries
184 senses
22 variants
0 examples
Object languages: qaa
Meta languages: tpi, en
```

## List values for a given field

Print all the values for a given field. For instance, for extracting the list of categories:

```console
$ liftlex values --field=category tests/data/FlexLiftExport.lift
field      category
subfield           
0              Noun
1              Noun
2              Noun
3              Noun
4              Noun
..              ...
179            Noun
180       Adjective
181            Noun
182            Noun
183            Noun
```

Note that column headers are given on two rows: "field" and "subfield". Some fields have "subfield", i.e. several values for different language or type of information, for instance glosses in several languages:

```console
$ liftlex values --field=gloss tests/data/FlexLiftExport.lift
field   gloss        
lang       en     tpi
index                
0        road     rod
1        skin        
2      paddle   pulim
3        swim  waswas
```

See next section for the available fields.

## Available fields

Many commands take an -f argument for mentioning the field(s) one is interested in. In order to have a list of available fields together with their definition, type:

```console
$ liftlex fields tests/data/FlexLiftExport.lift

                                 xpath  level                               unique  mixed_content   value
ID                                   .      1                     FieldType.UNIQUE          False     @id
form                 lexical-unit/form      1      FieldType.UNIQUE_BY_OBJECT_LANG           True    text
variantform                       form      4      FieldType.UNIQUE_BY_OBJECT_LANG           True       .
morphtype    trait[@name='morph-type']      1                     FieldType.UNIQUE          False  @value
category              grammatical-info      2                     FieldType.UNIQUE          False  @value
gloss                            gloss      2  FieldType.MULTIPLE_WITH_OBJECT_LANG           True  ./text
definition             definition/form      2      FieldType.UNIQUE_BY_OBJECT_LANG           True       .
```

Commands accept field names `ID`, `form`, `variantform`, etc. Each field is described by the XPath expression pointing at it, relatively to the node of a level (entry, sense). Other fields can be added.

## Frequency count

```
liftlex count -f category tests/data/FlexLiftExport.lift 
             0
Noun       133
Adverb       5
Adjective   25
Verb        11
n            2
Pronoun      3
             5
```

## Convert into other data format

### Convert into csv

Conversion into CSV of a table as defined by a set of fields is done with:

```
$ liftlex convert --format=csv --field=form,gloss,ID pylift/tests/data/tiny.lift
field    form ID   gloss         parent_id
subfield  tww         en     tpi          
0         efe  1    road     rod         1
1         efe  1    skin                 1
2         hei  2  paddle   pulim         2
3         hei  2    swim  waswas         2
```

Data are tabulated on console output for readibility; data printed into a file or in a pipe is well-formed CSV; see `| cat` :

```console
$ liftlex convert --format=csv --field=form,gloss,ID tests/data/tiny.lift | cat
field,form,ID,gloss,gloss,parent_id
subfield,tww,,en,tpi,
0,efe,1,road,rod,1
1,efe,1,skin,,1
2,hei,2,paddle,pulim,2
3,hei,2,swim,waswas,2
```

Two options are available regarding the situation where one entry form has several glosses:

- by default, the parent fields are repeated in order to match the number of child fields, as in the previous example: several lines have the *efe* form, to match the two senses given for this item ('road', 'skin').
- Alternatively, with the `-aggregate` flag, child fields are aggregated
  - In that case, the optional `-aggresep` argument (default: `;`) give the string used between aggregated values

```console
$ liftlex convert --format=csv --aggregate --field=form,gloss,ID tests/data/tiny.lift 
field    form ID parent_id        gloss              
subfield  tww                        en           tpi
0         efe  1         1    road;skin          rod;
1         hei  2         2  paddle;swim  pulim;waswas
```

### Convert into CLDF wordlist

```console
$ liftlex --output=cldf convert --format=CLDFWordlist  --aggregate --field=form,gloss,ID tests/data/tiny.lift
```

## Command line help

```
$ liftlex -h
usage: liftlex [-h] [--verbose] [--output [OUTPUT]] {summary,fields,values,count,convert,validate} ... filename

Utilities for LIFT (lexicon interchange format) lexicon.

positional arguments:
  filename              Lift filename

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         output detailled information
  --output [OUTPUT], -o [OUTPUT]
                        output file (or standard output if not specified)

subcommand:
  one valid subcommand

  {summary,fields,values,count,convert,validate}
                        subcommand: the main action to run. See `subcommand -h` for more info
    summary             Print summary about the lexicon
    fields              List the available fields in the dictionary that can be refered to in other commands
    values              List the values for the given field
    count               compute frequencies for the given field
    convert             Convert toward other formats
    validate            validation against LIFT schema
```

# See also

- [Lift XML vocabulary definition](https://code.google.com/archive/p/lift-standard/)
- [cldflex](https://pypi.org/project/cldflex/)
- [lift to latex conversion](https://github.com/sylvainloiseau/lift2latex)
