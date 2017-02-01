BottleGen
=========

Binary Format Reader/Writer Generator for C and Mercury 
-------------------------------------------------------

BottleGen reads in json descriptions of binary file blocks, and outputs C or Mercury code that reads the described 
format. It is not intended to handle all possible binary formats, but rather to aid in creating new binary formats
that will have a reasonable representation in Mercury and C.

Writing a Simple Binary Format
------------------------------

A simple format without any optional/dependant blocks can be written as a JSON object with the field names and types:

```
{
  "blocks"{
      "block":{
      "version":"int",
      "some_integer":"int",
      "some_other_integer":"int",
      "some_string":"string"
    }
  }
}
```

We have to put all blocks inside a "block" object, and each block must have a name (in this case, just "block"). This 
will generate readers and writers that can read/write blocks which have these properties.

###A Note on Strings in C:###

In C, strings are represented as a non-null-terminated object, instead specifying their length. On destruction, all 
strings must have their `str` field manually freed. This is intended to allow you keep just certain values from a block, 
but free the containing structure.

Writing Enum-Based Formats
--------------------------

Most formats have some kind of variability in their structure. BottleGen handles this with an enumeration that determines 
what kind of block to read, followed by a set of blocks which correspond to the enum values.

To define an enum, use a first-level object called "enums":

```
{
  "enums":{
    "some_enum":[
      "value1",
      "value2"
    ],
    "some_other_enum":[
      "value3",
      "value4"      
    ]
  }

}
```

It is highly recommended that each enum have unique value names. Repeating any value name can cause incorrect code to be 
generated except in very specific circumstances.

To make a set of blocks that depend on some enum, give an existing block a member called "children". This "children" 
block must have a member called "enum", and each of its other members must be named the same as values in the enum 
specified. As an example, here is a base-level block depending on a two-value enum:

```
{
  "enums":{
    "int_or_float_value":["int_value", "float_value"]
  }
  "blocks":{
    "block":{
      "children":{
        "enum":"int_or_float_value",
        "int_value":{
          "value":"int"
        },
        "float_value":{
          "value":"float"
        }
      }
    }
  }
}
```

Each block may only have a single "children" member, and each child must be named after an enum value.

Nested Enum-Based Children
--------------------------

A block's children are treated as first-class blocks themselves, so a child can have enum-based children as well. For 
instance, let's define a block named `something` that has a string called `name`, and a child that is type `a` or `b`. A 
child of type `a` has xy float coords, and type `b` has an integer `id`, and a type of either `c` with xy float coords or 
type `d` with a string named `ref`.

```
{
  "enums":{
    "child_type":[
      "a",
      "b"
    ],
    "b_type":[
      "c",
      "d"
    ]
  },
  "blocks":{
    "something":{
      "name":"string",
      "children":{
        "enum":"child_type",
        "a":{
          "x":"float",
          "y":"float"
        }
        "b":{
          "id":"int",
          "children":{
            "enum":"b_type",
            "c":{
              "x":"float",
              "y":"float"
            },
            "d":{
              "ref":"string"
            }
          }
        }
      }
    }
  }
}
```

Using BottleGen-based Writers/Readers
-------------------------------------

One important note is that BottleGen does NOT create fully formed file readers and writers. Rather, it is intended to 
create readers and writers for components of files. Usually for a reader, you will want to read a header (either 
described by a BottleGen block or by hand), and then decide which and how many BottleGen blocks to read after that. For a 
writer, you will similarly want to write a header, and then write out BottleGen blocks based on your data.

The decision to not create full file readers/writers was made because actually choosing which blocks to write based on 
previous blocks (beyond enumeration-based blocks) quickly adds complexity to the block description, and makes the 
generated readers and writers much more complex. Usually, to the application's author it is much easier to make these 
decisions.

License
-------

BottleGen is distributed under the 3-Clause BSD license (see the license file). Any generated code may be distributed 
under any license the user chooses.
