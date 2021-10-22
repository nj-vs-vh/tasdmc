
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define NT 0 // required in corsika2geant constants but not used in this program
#include "./corsika2geant/constants.h"

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        fprintf(
            stderr,
            "check_gea_dat_file accepts exactly 1 command-line arguments:\n"
            "\tTile (DATnnnnnn_gea.dat) file path\n");
        exit(EXIT_FAILURE);
    }
    const char *infile = argv[1];

    float eventbuf[NWORD];
    unsigned short buf[6];
    int parttype;
    float energy, height, theta, phi_orig;
    int m, n;
    float tmpedep[2];
    int tmptime;
    float pztmp;
    int n_problems = 0;
    FILE *f = 0;
    int verbosity = 1;

    f = fopen(infile, "rb");
    if (!f)
    {
        fprintf(stderr, "Error: file '%s' not found\n", infile);
        return 2;
    }
    if (!fread(eventbuf, sizeof(float), NWORD, f))
    {
        fprintf(stderr, "error: failed to read header from %s\n", infile);
        n_problems++;
        return n_problems;
    }
    parttype = (int)eventbuf[2];
    energy = eventbuf[3] / 1.e9;
    height = eventbuf[6];
    theta = eventbuf[10];
    phi_orig = eventbuf[11];
    if (verbosity >= 1)
    {
        fprintf(stdout, "%s\nparttype=%d energy=%f height=%f theta=%f phi_orig=%f\n",
                infile, parttype, energy, height, 180.0 / M_PI * theta, 180.0 / M_PI * phi_orig);
        fflush(stdout);
    }
    while (fread(buf, sizeof(short), 6, f) == 6)
    {
        m = (int)buf[0];
        n = (int)buf[1];
        if (m >= NX)
        {
            if (verbosity >= 2)
                fprintf(stderr, "m=%d is too large, maximum is %d\n", m, NX - 1);
            n_problems++;
        }
        if (n >= NY)
        {
            if (verbosity >= 2)
                fprintf(stderr, "n=%d is too large, maximum is %d\n", n, NY - 1);
            n_problems++;
        }
        tmpedep[0] = (float)buf[2];
        tmpedep[1] = (float)buf[3];
        tmptime = (int)buf[4];
        pztmp = (float)buf[5];
        if (verbosity >= 2)
        {
            fprintf(stdout, "%5d %5d %6.3e %6.3e %5d %6.3e\n", m, n, tmpedep[0], tmpedep[1], tmptime, pztmp);
            fflush(stdout);
        }
    }
    fclose(f);
    if (n_problems == 0)
        fprintf(stdout, "OK\n");
    else
        fprintf(stdout, "FAIL\n");
    fflush(stdout);
    return n_problems;
}
