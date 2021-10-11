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

// THESE WILL LIVE IN THEIR OWN HEADERS

// double corsika_times_th(char *filename);
// double corsika_vem_th(char *filename, int tcount);
// double corsika_vem(char *filename, char *tmpfile, int tcount);
// double corsika_vem_init(char *filename, char *tmpfile, int tcount);
// void fill_time();
// void fill_vem();
