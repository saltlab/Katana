## Katana: Dual Slicing-Based Context for Learning Bug Fixes

**Abstract**: Contextual information plays a vital role for software developers when understanding and fixing a bug. Context can also be important in deep learning-based program repair to provide extra information about the bug and its fix. Existing techniques, however, treat context in an arbitrary manner, by extracting code in close proximity of the buggy statement within the enclosing file, class, or method, without any analysis to find actual relations with the bug. To reduce noise, they use a predefined maximum limit on the number of tokens to be used as context. We present a program slicing-based approach, in which instead of arbitrarily including code as context, we analyze statements that have a control or data dependency on the buggy statement. We propose a novel concept called dual slicing, which leverages the context of both buggy and fixed versions of the code to capture relevant repair ingredients. We present our technique and tool called Katana, the first to apply slicing-based context for a program repair task. The results show Katana effectively preserves sufficient information for a model to choose contextual information while reducing noise. We compare against four recent state-of-the-art context-aware program repair techniques. Our results show Katana fixes between 1.5 to 3.7 times more bugs than existing techniques.

## Paper
[Katana: Dual Slicing-Based Context for Learning Bug Fixes](https://arxiv.org/pdf/2205.00180.pdf),
Published at ACM Transactions on Software Engineering and Methodology (TOSEM), 2023.

## Project Structure
- The dual sliced data is present in `sliced_data.tar.gz` in the `./gnn-model/hoppity-data/`.
- The unsliced data is present in `unsliced_data.tar.gz` in the `./gnn-model/hoppity-data/`.

The project has three modules:

### Data collection
- Use the scripts in bug-miner for collecting one line diff data from github.

### JS Slicer
- Use the scripts in the slicer folder for generating dual backward slices.

### GNN Model
- Use the scripts in model folder for graph generation, model training and inferences.

Each of the folders contain instructions in their individual README.md files.
