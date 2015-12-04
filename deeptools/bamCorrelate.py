#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import sys
import argparse
import numpy as np

import deeptools.countReadsPerBin as countR
from deeptools import parserCommon
from deeptools._version import __version__


def parse_arguments(args=None):
    parser = \
        argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="""
bamCorrelate computes the overall similarity between two or more BAM
files based on read coverage (number of reads) within genomic regions.
The correlation analysis is performed for the entire genome by running
the program in 'bins' mode, or for certain user selected regions in 'BED-file'
mode. Because the computation of the coverage is time consuming the program
outputs an intermediary file that can then be used with the 'plotCorrelation' tool
for visualizing the correlation.


detailed sub-commands help available under:

  bedCorrelate bins -h

  bedCorrelate BED-file -h

""",
           epilog='example usages:\n%(prog)s bins --bamfiles file1.bam file2.bam -out results.npz \n\n'
                  '%(prog)s BED-file --BED selection.bed --bamfiles file1.bam file2.bam \n'
                  '-out results.npz'
                  ' \n\n',
           conflict_handler='resolve')

    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    subparsers = parser.add_subparsers(
        title="commands",
        dest='command',
        description='subcommands',
        help='subcommands',
        metavar='')

    parent_parser = parserCommon.getParentArgParse(binSize=False)
    read_options_parser = parserCommon.read_options()

    # bins mode options
    bins_mode = subparsers.add_parser(
        'bins',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[bamcorrelate_args(case='bins'),
                 parent_parser, read_options_parser,
                 ],
        help="The correlation is based on read coverage over "
             "consecutive bins of equal "
             "size (10k bp by default). This mode is useful to assess the "
             "overall similarity of BAM files. The bin size and the "
             "distance between bins can be adjusted.",
        add_help=False,
        usage='%(prog)s '
              '--bamfiles file1.bam file2.bam '
              '-out results.npz \n')

    # BED file arguments
    bed_mode = subparsers.add_parser(
        'BED-file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[bamcorrelate_args(case='BED-file'),
                 parent_parser, read_options_parser,
                 ],
        help="The user provides a BED file that contains all regions "
             "that should be considered for the correlation analysis. A "
             "common use is to compare ChIP-seq coverages between two "
             "different samples for a set of peak regions.",
        usage='%(prog)s --BED selection.bed --bamfiles file1.bam file2.bam -out results.npz\n',
        add_help=False)

    return parser


def bamcorrelate_args(case='bins'):
    parser = argparse.ArgumentParser(add_help=False)
    required = parser.add_argument_group('Required arguments')

    # define the arguments
    required.add_argument('--bamfiles', '-b',
                          metavar='FILE1 FILE2',
                          help='List of indexed bam files separated by spaces.',
                          nargs='+',
                          required=True)

    required.add_argument('--outFileName', '-out',
                          help='File name to save the coverage matrix. This matrix '
                               'can be subsequently plotted using plotCorrelation or '
                               'or plotPCA.',
                          type=argparse.FileType('w'),
                          required=True)

    optional = parser.add_argument_group('Optional arguments')

    optional.add_argument("--help", "-h", action="help",
                          help="show this help message and exit")
    optional.add_argument('--labels', '-l',
                          metavar='sample1 sample2',
                          help='User defined labels instead of default labels from '
                               'file names. '
                               'Multiple labels have to be separated by space, e.g. '
                               '--labels sample1 sample2 sample3',
                          nargs='+')

    if case == 'bins':
        optional.add_argument('--binSize', '-bs',
                              metavar='INT',
                              help='Length in base pairs for a window used '
                                   'to sample the genome.',
                              default=10000,
                              type=int)

        optional.add_argument('--distanceBetweenBins', '-n',
                              metavar='INT',
                              help='By default, bamCorrelate considers consecutive '
                              'bins of the specified --binSize. However, to '
                              'reduce the computation time, a larger distance '
                              'between bins can by given. Larger distances '
                              'result in less bins being considered.',
                              default=0,
                              type=int)

        required.add_argument('--BED',
                              help=argparse.SUPPRESS,
                              default=None)
    else:
        optional.add_argument('--binSize', '-bs',
                              help=argparse.SUPPRESS,
                              default=10000,
                              type=int)

        optional.add_argument('--distanceBetweenBins', '-n',
                              help=argparse.SUPPRESS,
                              metavar='INT',
                              default=0,
                              type=int)

        required.add_argument('--BED',
                              help='Limits the correlation analysis to '
                              'the regions specified in this file.',
                              metavar='bedfile',
                              type=argparse.FileType('U'),
                              required=True)

    group = parser.add_argument_group('Output optional options')

    group.add_argument('--outRawCounts',
                       help='Save raw counts (coverages) to file.',
                       metavar='FILE',
                       type=argparse.FileType('w'))

    return parser


def process_args(args=None):
    args = parse_arguments().parse_args(args)

    if args.labels and len(args.bamfiles) != len(args.labels):
        print "The number of does not match the number of bam files."
        exit(0)
    if not args.labels:
        args.labels = map(lambda x: os.path.basename(x), args.bamfiles)

    return args


def main(args=None):
    """
    1. get read counts at different positions either
    all of same length or from genomic regions from the BED file

    2. save data for further plotting

    """
    args = process_args(args)

    if len(args.bamfiles) < 2:
        print "Please input at least two bam files to compare"
        exit(1)

    if 'BED' in args:
        bed_regions = args.BED
    else:
        bed_regions = None

    stepsize = args.binSize + args.distanceBetweenBins
    c = countR.CountReadsPerBin(
        args.bamfiles,
        args.binSize,
        0,
        defaultFragmentLength=args.fragmentLength,
        numberOfProcessors=args.numberOfProcessors,
        verbose=args.verbose,
        region=args.region,
        bedFile=bed_regions,
        extendPairedEnds=args.extendPairedEnds,
        minMappingQuality=args.minMappingQuality,
        ignoreDuplicates=args.ignoreDuplicates,
        center_read=args.centerReads,
        samFlag_include=args.samFlagInclude,
        samFlag_exclude=args.samFlagExclude,
        stepSize=stepsize,
        zerosToNans=False,
        out_file_for_raw_data=args.outRawCounts)

    num_reads_per_bin = c.run()

    sys.stderr.write("Number of bins "
                     "found: {}\n".format(num_reads_per_bin.shape[0]))

    if num_reads_per_bin.shape[0] < 2:
        exit("ERROR: too few non zero bins found.\n"
             "If using --region please check that this "
             "region is covered by reads.\n")

    np.savez_compressed(args.outFileName,
             matrix=num_reads_per_bin,
             labels=args.labels)


    if args.outRawCounts:
        # append to the generated file the
        # labels
        header = "#'chr'\t'start'\t'end'\t"
        header += "'" + "'\t'".join(args.labels) + "'\n"
        #import ipdb;ipdb.set_trace()
        with open(args.outRawCounts.name, 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(header + content)
    args.outRawCounts.close()


if __name__ == "__main__":
    main()