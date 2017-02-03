#!/usr/bin/env python

# ----------------------------------------------------------------------------
# Copyright (c) 2014--, tax-credit development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------


from unittest import TestCase, main
import pandas as pd
from shutil import rmtree
from os import remove, makedirs
from os.path import exists
from tax_credit.framework_functions import (generate_simulated_datasets,
                                            find_last_common_ancestor,
                                            novel_taxa_classification_evaluation,
                                            extract_per_level_accuracy)
from tax_credit.taxa_manipulator import (import_to_list,
                                         import_taxonomy_to_dict,
                                         compile_reference_taxa,
                                         extract_taxa_names)


class EvalFrameworkTests(TestCase):
    @classmethod
    def setUpClass(self):
        if not exists('test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1/'):
            makedirs('test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1/')
        with open('test_tmp/ref1.txt', 'w') as out:
            out.write(ref1)
        with open('test_tmp/B1-REF-L6-iter0/query_taxa.tsv', 'w') as out:
            out.write(taxa1)
        with open('test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1/query_tax_assignments.txt', 'w') as out:
            out.write(taxa2)

        self.databases = {'B1-REF': ['test_tmp/ref1.txt',
                                     'test_tmp/B1-REF-L6-iter0/query_taxa.tsv',
                                     "ref1", "GTGCCAGCMGCCGCGGTAA",
                                     "ATTAGAWACCCBDGTAGTCC", "515f", "806r"]}
        self.ref_data = pd.DataFrame.from_dict(self.databases, orient="index")
        self.ref_data.columns = ["Reference file path", "Reference tax path",
                                 "Reference id", "Fwd primer", "Rev primer",
                                 "Fwd primer id", "Rev primer id"]

        self.exp_p = [0, 1.0, 1.0, 0.875, 0.8571428571428571,
                      0.83333333333333337, 0.66666666666666663]
        self.exp_r = [0, 1.0, 1.0, 0.875, 0.75, 0.625, 0.25]
        self.exp_f = [0, 1.0, 1.0, 0.875, 0.79999999999999993,
                      0.7142857142857143, 0.36363636363636365]
        self.exp_m = [0, 0, 0, 1, 1, 1, 3, 2]

    def test_generate_simulated_datasets(self):
        generate_simulated_datasets(self.ref_data, 'test_tmp', 100, 2, range(6, 5, -1))
        # cross-validated should include only acidilacti and brevis, one rep in both query and ref
        cv_taxa = set(import_to_list('test_tmp/cross-validated/B1-REF-iter0/query_taxa.tsv', field=1) +
                      import_to_list('test_tmp/cross-validated/B1-REF-iter1/query_taxa.tsv', field=1))
        cv_ref = set(import_to_list('test_tmp/cross-validated/B1-REF-iter0/ref_taxa.tsv', field=1) +
                     import_to_list('test_tmp/cross-validated/B1-REF-iter1/ref_taxa.tsv', field=1))
        self.assertEqual(cv_taxa, {'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus; s__brevis',
                                   'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus; s__acidilactici'})
        self.assertEqual(cv_taxa & cv_ref, {'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus; s__brevis',
                                            'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus; s__acidilactici'})
        # confirm that query seq IDs are not in ref for cross-val
        for i in [0, 1]:
            # test that cross-validated queries have pair in ref, but keys do not match
            query_taxa = import_taxonomy_to_dict('test_tmp/cross-validated/B1-REF-iter{0}/query_taxa.tsv'.format(i))
            ref_taxa = import_taxonomy_to_dict('test_tmp/cross-validated/B1-REF-iter{0}/ref_taxa.tsv'.format(i))
            for key, value in query_taxa.items():
                # seq ID keys do not match
                self.assertNotIn(key, ref_taxa)
                # but matching taxonomy is present for each query taxon.
                self.assertIn(value, ref_taxa.values())
            # test that novel-taxa queries have no match in ref
            query_taxa = import_taxonomy_to_dict('test_tmp/novel-taxa-simulations/B1-REF-L6-iter{0}/query_taxa.tsv'.format(i))
            ref_taxa = import_taxonomy_to_dict('test_tmp/novel-taxa-simulations/B1-REF-L6-iter{0}/ref_taxa.tsv'.format(i))
            taxa = [t.split(';')[5] for t in ref_taxa.values()]
            for key, value in query_taxa.items():
                self.assertNotIn(key, ref_taxa)
                self.assertNotIn(value, ref_taxa.values())
                self.assertIn(value.split(';')[5], taxa)

    def test_find_last_common_ancestor(self):
        taxa1 = import_to_list('test_tmp/B1-REF-L6-iter0/query_taxa.tsv')
        taxa2 = import_to_list('test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1/query_tax_assignments.txt')
        t1 = extract_taxa_names(taxa1, level=slice(None), field=1)
        t2 = extract_taxa_names(taxa2, level=slice(None), field=1)
        for i, n in zip(range(8), [7, 6, 5, 4, 7, 3, 6, 6]):
            self.assertEqual(find_last_common_ancestor(
                t2[i].split(';'), t1[i].split(';')), n)

    def test_novel_taxa_classification_evaluation(self):
        # test novel taxa evaluation
        results = novel_taxa_classification_evaluation(
            ['test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1'],
            'test_tmp', 'test_tmp/summary.txt', test_type='novel-taxa')
        self.assertEqual(results.iloc[0]['Dataset'], 'B1-REF')
        self.assertEqual(int(results.iloc[0]['level']), 6)
        self.assertEqual(int(results.iloc[0]['iteration']), 0)
        self.assertEqual(results.iloc[0]['Method'], 'method1')
        self.assertEqual(results.iloc[0]['Parameters'], 'param1')
        self.assertEqual(results.iloc[0]['match_ratio'], 0.375)
        self.assertEqual(results.iloc[0]['overclassification_ratio'], 0.25)
        self.assertEqual(results.iloc[0]['underclassification_ratio'], 0.25)
        self.assertEqual(results.iloc[0]['misclassification_ratio'], 0.125)
        self.assertEqual(results.iloc[0]['Precision'], 0.5)
        self.assertEqual(results.iloc[0]['Recall'], 0.375)
        self.assertEqual(results.iloc[0]['F-measure'], 0.42857142857142855)
        self.assertEqual(results.iloc[0]['mismatch_level_list'], self.exp_m)
        # test cross-validated evaluation
        results = novel_taxa_classification_evaluation(
            ['test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1'],
            'test_tmp', 'test_tmp/summary.txt', test_type='cross-validated')
        self.assertEqual(results.iloc[0]['Dataset'], 'B1-REF-L6')
        self.assertEqual(int(results.iloc[0]['iteration']), 0)
        self.assertEqual(results.iloc[0]['Method'], 'method1')
        self.assertEqual(results.iloc[0]['Parameters'], 'param1')
        self.assertEqual(results.iloc[0]['match_ratio'], 0.25)
        self.assertEqual(results.iloc[0]['overclassification_ratio'], 0)
        self.assertEqual(results.iloc[0]['underclassification_ratio'], 0.625)
        self.assertEqual(results.iloc[0]['misclassification_ratio'], 0.125)
        self.assertEqual(results.iloc[0]['Precision'], self.exp_p)
        self.assertEqual(results.iloc[0]['Recall'], self.exp_r)
        self.assertEqual(results.iloc[0]['F-measure'], self.exp_f)
        self.assertEqual(results.iloc[0]['mismatch_level_list'], self.exp_m)

    def test_extract_per_level_accuracy(self):
        results = novel_taxa_classification_evaluation(
            ['test_tmp/B1-REF-L6-iter0/B1-REF-L6-iter0/method1/param1'],
            'test_tmp', 'test_tmp/summary.txt', test_type='cross-validated')
        pla = extract_per_level_accuracy(results)
        # confirm that method/dataset data propagate properly
        self.assertEqual(pla['Dataset'].unique(), ['B1-REF-L6'])
        self.assertEqual(pla['iteration'].unique(), ['0'])
        self.assertEqual(pla['Method'].unique(), ['method1'])
        self.assertEqual(pla['Parameters'].unique(), ['param1'])
        # confirm that level and per-level results are correct
        for i, p, r, f in zip(range(6), self.exp_p, self.exp_r, self.exp_f):
            self.assertEqual(pla.iloc[i]['level'], i + 1)
            self.assertEqual(pla.iloc[i]['Precision'], self.exp_p[i + 1])
            self.assertEqual(pla.iloc[i]['Recall'], self.exp_r[i + 1])
            self.assertEqual(pla.iloc[i]['F-measure'], self.exp_f[i + 1])
            self.assertEqual(pla.iloc[i]['match_ratio'], self.exp_r[i + 1])

    @classmethod
    def tearDownClass(self):
        rmtree('test_tmp/')




ref1 = """>179419
TGAGAGTTTGATCCTGGCTCAGGACGAACGCTGGCGGCATGCCTAATACATGCAAGTCGAACGAGCTTCCGTTGAATGACGTGCTTGCACTGATTTCAACAATGAAGCGAGTGGCGAACTGGTGAGTAACACGTGGGGAATCTGCCCAGAAGCAGGGGATAACACTTGGAAACAGGTGCTAATACCGTATAACAACAAAATCCGCATGGATCTTGTTTGAAAGGTGGCTTCGGCTATCACTTCTGGATGATCCCGCGGCGTATTAGTTAGTTGGTGAGGTAAAGGCCCACCAAGACGATGATACGTAGCCGACCTGAGAGGGTAATCGGCCACATTGGGACTGAGACACGGCCCAAACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCACAATGGACGAAAGTCTGATGGAGCAATGCCGCGTGAGTGAAGAAGGGTTTCGGCTCGTAAAACTCTGTTGTTAAAGAAGAACACCTTTGAGAGTAACTGTTCAAGGGTTGACGGTATTTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTGTCCGGATTTATTGGGCGTAAAGCGAGCGCAGGCGGTTTTTTAAGTCTGATGTGAAAGCCTTCGGCTTAACCGGAGAAGTGCATCGGAAACTGGGAGACTTGAGTGCAGAAGAGGACAGTGGAACTCCATGTGTAGCGGTGGAATGCGTAGATATATGGAAGAACACCAGTGGCGAAGGCGGCTGTCTAGTCTGTAACTGACGCTGAGGCTCGAAAGCATGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCATGCCGTAAACGATGAGTGCTAAGTGTTGGAGGGTTTCCGCCCTTCAGTGCTGCAGCTAACGCATTAAGCACTCCGCCTGGGGAGTACGACCGCAAGGTTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCTACGCGAAGAACCTTACCAGGTCTTGACATCTTCTGCCAATCTTAGAGATAAGACGTTCCCTTCGGGGACAGAATGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTATTATCAGTTGCCAGCATTCAGTTGGGCACTCTGGTGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAACGAGTCGCGAAGTCGTGAGGCTAAGCTAATCTCTTAAAGCCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGTTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCATGAGAGTTTGTAACACCCAAAGCCGGTGAGATAACCTTCGGGAGTCAGCCGTCTAAGGTGGGACAGATGATTAGGGTGAAGTCGTAACAAGGTAGCCGTAGGAGAACCTGCGGCTGGATCACCTCCTTTCT
>1117026
GAGTGGCGAACTGGTGAGTAACACGTGGGAAATCTGCCCAGAAGCAGGGGATAACACTTGGAAACAGGTGCTAATACCGTATAACAACAAGAACCGCATGGTTCTTGTTTGAAAGGTGGTTTCGGCTATCACTTCTGGATGATCCCGCGGCGTATTAGTTAGTTGGTGAGGTAAAGGCCCACCAAGACAATGATACGTAGCCGACCTGAGAGGGTAATCGGCCACATTGGGACTGAGACACGGCCCAAACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCACAATGGACGAAAGTCTGATGGAGCAATGCCGCGTGAGTGAAGAAGGGTTTCGGCTCGTAAAACTCTGTTGTTAAAGAAGAACACCTCTGAGAGTAACTGTTCAGGGGTTGACGGTATTTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTGTCCGGATTTATTGGGCGTAAAGCGAGCGCAGGCGGTTTCTTAAGTCTGATGTGAAAGCCTTCGGCTTAACCGGAGAAGTGCATCGGAAACTGGGTAACTTGAGTGCAGAAGAGGACAGTGGAACTCCATGTGTAGCGGTGGAATGCGTAGATATATGGAAGAACACCAGTGGCGAAGGCGGCTGTCTAGTCTGTAACTGACGCTGAGGCTCGAAAGCATGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCATGCCGTAAACGATGAGTGCTAGGTGTTGGAGGGTTTCCGCCCTTCAGTGCCGCAGCTAACGCATTAAGCACTCCGCCTGGGGAGTACGACCGCAAGGTTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCTACGCGAAGAACCTTACCAGGTCTTGACATACTATGCAAACCTAAGAGATTAGGCGTTCCCTTCGGGGACATGGATACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTATTATCAGTTGCCAGCATTCAGTTGGGCACTCTGGTGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAACGAGTTGCGAAGTCGTGAGGCTAAGCTAATCTCTTAAAGCCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGTTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCATGAGAGTTTGTAACACCCAAAGCCGGTGAGATAACCTTCGGGAGTCAGCCGTCTATAGTG
>192680
AGAGTTTGATCCTGGCTCAGGACGAACGCTGGCGGCGTGCCTAATACATGCAAGTCGAACGAAGCCTTCTTTCACCGAATGTTTGCATTCACCGAAAGAAGCTTAGTGGCGAACGGGTGAGTAACACGTAGGCAACCTGCCCAAAAGAGGGGGATAACACTTGGAAACAGGTGCTAATACCGCATAACCATGAACACCGCATGATGTTCATGTAAAAGGCGGCTTTTGCTGTCACTTTTGGATGGGCCTGCGGCGTATTAACTTGTTGGTGGGGTAACGGCCTACCAAGGTGATGATACGTAGCCGAACTGAGAGGTTGATCGGCCACATTGGGACTGAGACACGGCCCAAACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCACAATGGACGAAAGTCTGATGGAGCAACGCCGCGTGAATGAAGAAGGCCTTCGGGTCGTAAAATTCTGTTGTCAGAGAAGAACGTGCGTGAGAGTAACTGTTCACGTATTGACGGTATCTGATCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCGAGCGTTGTCCGGATTTATTGGGCGTAAAGGGAACGCAGGCGGTCTTTTAAGTCTGATGTGAAAGCCTTCGGCTTAACCGAAGTAGTGCATTGGAAACTGGAAGACTTGAGTGCAGAAGAGGAGAGTGGAACTCCATGTGTAGCGGTGAAATGCGTAGATATATGGAAGAACACCAGTGGCGAAAGCGGCTCTCTGGTCTGTAACTGACGCTGAGGTTCGAAAGCGTGGGTAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTGGAGGGTTTCCGCCCTTCAGTGCTGCAGCTAACGCATTAAGCACTCCGCCTGGGGAGTACGGTCGCAAGACTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCTTCTGACAATTCTAGAGATGGAACGTTCCCTTCGGGGACAGAATGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTATTGTCAGTTGCCATCATTAAGTTGGGCACTCTGGCGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAACGAGTCGCTAACTCGCGAGGGCAAGCTAATCTCTTAAAGCCGTTCTCAGTTCGGACTGCAGGCTGCAACCCGCCTGCACGAAGTTGGAATTGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGTCTTGCACTCACCGCCCGTCA
>2562098
AGAGTTTGATCCTGGCTCAGGACGAACGCTGGCGGCGTGCCTAATACATGCAAGTCGAGCGGATCATCGGGAGCTTGCTCCCGATGATCAGCGGCGGACGGGTGAGTAACACGTGGGCAACCTGCCTGTAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAATTCATCTCCTCTCATGAGGGGATGCTGAAAGACGGTTTCGGCTGTCACTTACAGATGGGCCCGCGGCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGCGAAGAAGGCCTTCGGGTCGTAAAGCTCTGTTGTCAGGGAAGAACAAGTACCGGAGTAACTGCCGGTACCTTGACGGTACCTGACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTGTCCGGAATTATTGGGCGTAAAGCGCGCGCAGGCGGTCCTTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGGGACTTGAGTGCAGAAGAGGAGAGCGGAATTCCACGTGTAGCGGTGAAATGCGTAGAGATGTGGGGGAACACCAGTGGCGAAGGCGGCTCTCTGGTCTGTAACTGACGCTGAGGCGCGAAAGCGTGGGGAGCGAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGCAGCAAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGCCACTCCTGGAGACAGGACGTTCCCCTTCGGGGGACAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGTTCTTAGTTGCCAGCATTCAGTTGGGCGCTCTAAGGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTGCAATGGATAGAACAAAGGGCAGCGAAGCCGCGAGGTGAAGCCAATCCCATAAATCTATTCTCAGTTCGGATTGCAGGCTGCAACTCGCCTGCATGAAGCCGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGTTTGTAACACCCGAAGTCGGTGGGGTAACCTTTTGGAGCCAGCCGCCTAAGGTGGGACAGATGATTGGGGTGAAGTCGTAACAAGGTA
>4308624
CTTTATTGGAGAGTTTGATCCTGGCTCAGGATGAACGCTGGCGGCGTGCCTAATACATGCAAGTCGAGCGAATGGATTGAGAGCTTGCTCTCAAGAAGTTAGCGGCGGACGGGTGAGTAACACGTGGGTAACCTGCCCATAAGACTGGGATAACTCCGGGAAACCGGGGCTAATACCGGATAACATTTTGAACCGCATGGTTCGAAATTGAAAGGCGGCTTTGGCTGTCACTTATGGATGGACCCGCGTCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAACGATGCGTAGCCGACCTGAGAGGGTGATCGGCCACACTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCGCAATGGACGAAAGTCTGACGGAGCAACGCCGCGTGAGTGATGAAGGCTTTCGGGTCGTAAAACTCTGTTGTTAGGGAAGAACAAGTGCTAGTTGAATAAGCTGGCACCTTGACGGTACCTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGAATTATTGGGCGTAAAGCGCGCGCAGGTGGTTTCTTAAGTCTGATGTGAAAGCCCACGGCTCAACCGTGGAGGGTCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGAAAGTGGAATTCCATGTGTAGCGGTGAAATGCGTAGAGATATGGAGGAACACCAGTGGCGAAGGCGACTTTCTGGTCTGTAACTGACACTGAGGCGCGAAAGCGTGGGGAGCAAACAGGATTAGATACCCTGGTAGTCCACGCCGTAAACGATGAGTGCTAAGTGTTAGAGGGTTTCCGCCCTTTAGTGCTGAAGTTAACGCATTAAGCACTCCGCCTGGGGAGTACGGCCGCAAGGCTGAAACTCAAAGGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCAACGCGAAGAACCTTACCAGGTCTTGACATCCTCTGAAAACCCTAGAGATAGGGCTTCTCCTTCGGGAGCAGAGTGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTGATCTTAGTTGCCATCATTAAGTTGGGCACTCTAAGGTGACTGCCGGTGACAAACCGGAGGAAGGTGGGGATGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAAAGAGCTGCAAGACCGCGAGGTGGAGCTAATCTCATAAAACCGTTCTCAGTTCGGATTGTAGGCTGCAACTCGCCTACATGAAGCTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCACGAGAGTTTGTAACACCCGAAGTCGGTGGGGTAACCTTTATGGAGCCAGCCGCCTAAGGTGGGACAGATGATTGGGGTGAAGTCGTAACAAGGTAGCCGTATCGGAAGGTGCGGCTGGATCACCTCCTTTCT
>102222
GCGAACGGGTGAGTAACAGGTGGGTACCTGCCCAGAAGCAGGGGATAACACTTGGAAACAGATGTTAATCCCGTATAACAAAAGAAACCCGCTTGTTTTTCTTTAAAAAGATGGTTGTGCTTATCACTTTTGATGGACCCGGGGCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCAATGATGCGTAGCCGACTTGAGAGGGTAATCGCCACATTGGGATTGAGACACGGCCCAGACTCTACGGGAGCAGCAGTAGGGAATCTTCCACCAATGGACGCAAGTCTGATGGAGCAACGCCGCGTGAGTGAAGAAGGGTTTCGGCTCGTAAAGCTCTGTTGTTAAAGAAGAACGTGGGTGAGAGTAACTGTTCACCCAGTGACGGTATTTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGATTTATTGGGCGTAAAGCGAGCGCAGGCGGTCTTTTAAGTCTAATGTGAAAGCCTTCGGCTCAACCGAAGAAGTGCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGACAGTGGAACTCCATGTGTAGCGGTGAAATGCGTAGATATATGGAAGAACACCAGTGGCGAAGGCGGCTGTCTGGTCTGTAACTGACGCTGAGGCTCGAAAGCATGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCATGCCGTAAACGATGATTACTAAGTGTTGGAGGGTTTCCGCCCTTCAGTGCTGCAGCTAACGCATTAAGTAATCCGCCTGGGGAGTACGACCGCAAGGTTGAAACTCAAAAGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCTACGCGAAGAACCTTACCAGGTCTTGACATCTTCTGCCAACCTAAGAGATTAGGCGTTCCCTTCGGGGACAGAATGACAGGTGGTGCATGGTTGTCTTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCTTATTACTAGTTGCCAGCATTCAGTTGGGCACTCTAATGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGACGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGATGGGCAACGAGTCCCGAAACCGCGAGGTTAACTAATCTCTTAAAACCATTCTCAATTCGGACTGTAGGCTGCAACTCGCCTACACGAAGTCGGAATCGCTAGTAATCGCGGATCAACATGCCGCGGGGAATACGTTCCCGGGCCTTGTACACACCGCCGTCACACCATGAGAATTTGTACACCCAAAGCCGGTGGGGTACCTTTTAGACTACCGGCTAAAGTGGGGACAAATGATTAAGGTGAAGTCGTA
>27815
TAACCCGTGGGCACCTTGCCAAGAAGCAGGGGATAACCCTTGGAAAAGGTTGCTAATTCCGTATAACAGAGAAAACCGCCTTGGTTTTCTTTTAAAAGGATGGTTCTGCTATCACTTCTGGATGGACCCGCGGCGCATTAGCTAGTTGGTGAGGTAACGGCTCACCAAGGCGATGATGCGTAGCCGACCTGAGAGGTAACCGCCACATTGGACTGAGACACGGGCCAAGACCTCTACGGGAGGCAGAAGTAGGGAATCTTCGACAATGGACGAAAGTCTGATGGAGCAACGCCGCGTGAGTGAAGAAGGGTTTCGGATCGTAAAGCTCTGTTGTTAAAGAAGAACGTGGGTGAGAGTAACTGTTCACCCATTGACGGTATTTAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAACCGTTGATCCGGGATTTATTGGGCGTAAAGCGAGCGCAGGCGGTCTTTTAAGTCTAATGTTGAAAACTTCGGCTCAACCGAAGAAGTGCATTGGAAACTGGGAGACTTGAGTGCAGAAGAGGATAGTGGAACTCCATGTGTAGCGGTGAAATGCGTAGATATATGGAGGAACACCAGTGGCGAAGGCGGCTGCTCTGGTCTGTAACTGACGCTGAGGCTCGAAAGCATGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCATGCCGTAAACGATGATTACTAAGTGTTGGAGGGTTTCCGCCCTTCAGTGCTGCAGCTAACGCATTAAGTAATCCGCCTGGGGAGTACGACCGCAAGGTTGAAACTCAAAAGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCTACGCGAAGAACCTTACCAGGTCTTGACATCTTCTGCCAACCTAGAGATTAGGCGTTCCCTTCGGGGACAGAATGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGGCGCAACCCTTATTACTAGTTGCCAGCATTCAGTTGGGCACTCTAGTGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGACGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGGTGGTACAACGAGTTGCGAAACCGCGAGGTTTAAGCTAATCTCTTAAAACCATTCTCAGTTCGGACTGTAGGCTGCAACTCGCCTACACGAAGTCGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGGCCGTCACACCATGAGAGTTTGTAACAACCCAAGGCGGTTGGGTAACCTTTTAGGGGCTAGCCGTTTAAGGTGGGACAAATTATTAGGGGTGAAGTCGTAACAAGGTAACC
>1136710
GATGAACGCTGGCGGCGTGCCTAATACATGCAAGTCGGACGCACTTTCGTTGATTGAATTAGAGATGCTTGCATCGAAGATGATTTCAACTATAAAGTGAGTGGCGAACGGGTGAGTAACACGTGGGTAACCTGCCCAGAAGTGGGGGATAACACCTGGAAACAGATGCTAATACCGCATAATAAAATGAACCGCATGGTTTATTTTTAAAAGATGGCTTCGGCTATCACTTCTGGATGGACCCGCGGCGTATTAGCTAGTTGGTGAGATAAAGGCTCACCAAGGCTGTGATACGTAGCCGACCTGAGAGGGTAATCGGCCACATTGGGACTGAGACACGGCCCAGACTCCTACGGGAGGCAGCAGTAGGGAATCTTCCACAATGGACGAAAGTCTGATGGAGCAACGCCGCGTGAGTGATGAAGGCTTTAGGGTCGTAAAACTCTGTTGTTGGAGAAGAACGTGTGTGAGAGTAACTGCTCATGCAGTGACGGTATCCAACCAGAAAGCCACGGCTAACTACGTGCCAGCAGCCGCGGTAATACGTAGGTGGCAAGCGTTATCCGGATTTATTGGGCGTAAAGCGAGCGCAGGCGGTTTTTTAAGTCTAATGTGAAAGCCTTCGGCTTAACCGAAGAAGTGCATTGGAAACTGGGAAACTTGAGTGCAGAAGAGGACAGTGGAACTCCATGTGTAGCGGTGAAATGCGTAGATATATGGAAGAACACCAGTGGCGAAGGCGGCTGTCTGGTCTGTAACTGACGCTGAGGCTCGAAAGCATGGGTAGCGAACAGGATTAGATACCCTGGTAGTCCATGCCGTAAACGATGAATGCTAAGTGTTGGAGGGTTTCCGCCCTTCAGTGCTGCAGCTAACGCATTAAGCATTCCGCCTGGGGAGTACGACCGCAAGGTTGAAACTCAAAAGAATTGACGGGGGCCCGCACAAGCGGTGGAGCATGTGGTTTAATTCGAAGCTACGCGAAGAACCTTACCAGGTCTTGACATCTTCTGCTAACCTAAGAGATTAGGCGTTCCCTTCGGGGACAGAATGACAGGTGGTGCATGGTTGTCGTCAGCTCGTGTCGTGAGATGTTGGGTTAAGTCCCGCAACGAGCGCAACCCCTATTATTAGTTGCCAGCATTAAGTTGGGCACTCTAGTGAGACTGCCGGTGACAAACCGGAGGAAGGTGGGGACGACGTCAAATCATCATGCCCCTTATGACCTGGGCTACACACGTGCTACAATGGACGGTACAACGAGTTGCGAGACCGCGAGGTTAAGCTAATCTCTTAAAACCGTTCTCAGTTCGGACTGCAGGCTGCAACTCGCCTGCACGAAGTTGGAATCGCTAGTAATCGCGGATCAGCATGCCGCGGTGAATACGTTCCCGGGCCTTGTACACACCGCCCGTCACACCATGAGAGTTTGTAACACCCAAAGCCGGTGGAGTAACCTTCGGGAGCTAGCCGTCTAAGGTGGGACAGATGATTGGGGTGAAGTCGTAACAAGGTAGCCGTAGGAGAACCTGCGGCTGGATCACCTCCTTTCT"""

taxa1 = """179419	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus; s__brevis
1117026	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus; s__brevis
192680	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus; s__ruminis
2562098	k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; f__Bacillaceae; g__Bacillus; s__foraminis
4308624	k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; f__Bacillaceae; g__Bacillus; s__cereus
102222	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus; s__acidilactici
27815	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus; s__acidilactici
1136710	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus; s__damnosus"""

taxa2 = """179419	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus; s__brevis
1117026	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus
192680	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae
2562098	k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales
4308624	k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; f__Bacillaceae; g__Bacillus; s__cereus
102222	k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; f__Bacillaceae; g__Bacillus; s__cereus
27815	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus
1136710	k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Pediococcus"""


if __name__ == "__main__":
    main()
