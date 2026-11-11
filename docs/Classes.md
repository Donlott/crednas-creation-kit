# Classes

Choose **Classes** to edit class definitions. **Overview** holds name/help keys, movement and class-family links, appearance references and related values. **Skills & gear** covers equipment restrictions and class skills. **Promotion** covers linked classes and stored promotion requirements.

## Stats

The identified columns are labelled **Class bases**, **Class growth bonuses** and **Minimum stats**. Other blocks and enum values remain raw where their interpretation is unknown. Aptitude columns preserve their signed or unsigned storage limits.

## Create a class

Use **New class…** or **Duplicate class…** on **Overview**. A duplicate copies the selected class's current supported values and links into a new unique class ID. Original IDs and positions stay fixed.

Assign the class where needed and configure promotion/progression relationships separately. New definitions do not generate localized descriptions, appearance assets or gameplay rules automatically. Cyclic/invalid direct links and supported incoming references are checked where possible; runtime behavior still needs testing.

**Used by** shows supported current class references, including observed progression class-name cells, and can open their source entries. **Remove new class** applies only to newly created classes after supported references have been cleared.

[Guide home](Home.md)
