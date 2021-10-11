/* 
  This variable tells how much memory to use per corsika2geant process
  (NT variable roughly equals (memory in Gb) x 16)
  One should pass -DNT=32 (or some other number) on the command line 
  when compiling the program.
*/
#ifndef NT
#error Array size variable 'NT' has not been defined. Use -DNT=16, 32, 64, etc compilation option
#endif

int corsika2geant(const char *inputFile, const char *geantFile, const char *outputFile);
