
from pathlib import Path
import pandas as pd
from IPython import embed
import numpy as np
from tabulate import tabulate

from dataset import Dataset
from stats import StatisticalAnalysis

from topics import TOPICS
from scipy.sparse import vstack

def divergence_analysis(master_dataset:Dataset,
                        c1:Dataset,                 # sub corpus 1
                        c2:Dataset,                 # sub corpus 2
                        topics_or_terms='terms',
                        number_of_terms_to_print=30,
                        c1_name=None, c2_name=None,
                        print_results=True, sort_by=None,
                        min_appearances_per_term=50):
    if not c1_name:
        c1_name = c1.name
    if not c2_name:
        c2_name = c2.name

    if not sort_by:
        if topics_or_terms == 'topics':
            sort_by = 'frequency_score'
        else:
            sort_by = 'dunning'


    if topics_or_terms == 'terms':
        vocabulary = master_dataset.get_vocabulary(max_terms=10000,
                                                   min_appearances=min_appearances_per_term,
                                                   include_2grams=True)
        c1_dtm = c1.get_document_term_matrix(vocabulary=vocabulary)
        c2_dtm = c2.get_document_term_matrix(vocabulary=vocabulary)
    else:
        vocabulary = [f'topic.{i}' for i in range(1, 71)]
        c1_dtm = c1.get_document_topic_matrix() * 300
        c2_dtm = c2.get_document_topic_matrix() * 300

    master_dtm = vstack([c1_dtm, c2_dtm])

    s = StatisticalAnalysis(master_dtm, c1_dtm, c2_dtm, vocabulary)
    dunning, _ = s.dunning_log_likelihood()
    frequency_score, _ = s.frequency_score()
#    correlated_terms = s.correlation_coefficient()

    total_terms_all = master_dtm.sum()
    total_terms_c1 = c1_dtm.sum()
    total_terms_c2 = c2_dtm.sum()

    column_sums_all = np.array(master_dtm.sum(axis=0))[0]
    column_sums_c1 = np.array(c1_dtm.sum(axis=0))[0]
    column_sums_c2 = np.array(c2_dtm.sum(axis=0))[0]

    data = []
    for term_idx in range(len(vocabulary)):
        count_all = column_sums_all[term_idx]
        count_c1 = column_sums_c1[term_idx]
        count_c2 = column_sums_c2[term_idx]


        if topics_or_terms == 'terms':
            term = vocabulary[term_idx]
            if count_all < min_appearances_per_term:
                continue
        else:
            topic_idx = term_idx + 1
            term = f'({topic_idx}) {TOPICS[topic_idx]["name"]}'

        data.append({
            'term': term,
            'dunning': dunning[term_idx],
            'frequency_score': frequency_score[term_idx],
            'count_total': count_all,
            f'count {c1_name}': count_c1,
            f'count {c2_name}': count_c2,
            'frequency_total': count_all / total_terms_all,
            f'frequency {c1_name}': count_c1 / total_terms_c1,
            f'frequency {c2_name}': count_c2 / total_terms_c2,
#            'correlated_terms': correlated_terms[vocabulary[term_idx]]
        })
    df = pd.DataFrame(data)


    df.sort_values(by=sort_by, inplace=True)
    df.reset_index(inplace=True)

    if print_results:

        if topics_or_terms == 'topics':
            headers = ['term', 'dunning', 'frequency_score', 'frequency_total',
                       f'frequency {c1_name}', f'frequency {c2_name}']
        else:
            headers = ['term', 'dunning', 'frequency_score', 'count_total',
                       f'count {c1_name}', f'count {c2_name}']

        year_df = {}

        for years_range in [(1976, 1984), (1985, 1989), (1990, 1994), (1995, 1999), (2000, 2004),
                             (2005, 2009), (2010, 2015)]:
            y1, y2 = years_range
            c1_count = len(c1.df[(c1.df['ThesisYear'] >= y1) & (c1.df['ThesisYear'] <= y2)])
            c2_count = len(c2.df[(c2.df['ThesisYear'] >= y1) & (c2.df['ThesisYear'] <= y2)])
            if c1_count > 0 or c2_count > 0:
                year_df[f'{y1}-{y2}'] = {
                    f'{c1_name}': c1_count,
                    f'{c1_name} freq': c1_count / len(c1),
                    f'{c2_name}': c2_count,
                    f'{c2_name} freq': c2_count / len(c2),
                }
        year_df = pd.DataFrame(year_df).transpose()
        print(tabulate(year_df, headers='keys'))


        print(f'\n\nTerms distinctive for Corpus 1: {c1_name}. {len(c1)} Theses\n')
        print(tabulate(df[headers][::-1][0:number_of_terms_to_print], headers='keys'))

        print(f'\n\nTerms distinctive for Corpus 2: {c2_name}. {len(c2)} Theses\n')
        print(tabulate(df[headers][0:number_of_terms_to_print], headers='keys'))


    return df

def wordcloud(gender='female', relative_scaling=0.0):

    # local imports so Pillow and wordclouds are not hard requirements for running any code
    from PIL import Image, ImageFont, ImageDraw
    from wordcloud import WordCloud

    def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):

        color = icon.getpixel((int(position[1] + 2), int(position[0] + 2)))

        print(color)

        if color[0] == color[1] == color[2]: color = (0, 0, 0, 255)
        # if color[0] > 200: color = (220, 0, 0, 255)

        if (color[0] + color[1] + color[2]) > 230:
            print(word, color, font_size)
        return color

    if gender == 'female':
        icon_path = Path('data', 'plots', 'word_clouds', 'icon_female.png')
    else:
        icon_path = Path('data', 'plots', 'word_clouds', 'icon_male.png')

    icon = Image.open(icon_path)

    basewidth = 3000
    wpercent = (basewidth / float(icon.size[0]))
    hsize = int((float(icon.size[1]) * float(wpercent)))
    icon = icon.resize((basewidth, hsize))#, icon.ANTIALIAS)
    icon = icon.convert('RGBA')

    d = Dataset()
    c1 = d.copy().filter(author_gender='female')
    c2 = d.copy().filter(author_gender='male')
    data = divergence_analysis(d, c1, c2)

    mask = Image.new("RGBA", icon.size, (255, 255, 255))
    mask.paste(icon, icon)
    mask = np.array(mask)


    word_dict = {}
    for _, row in data.iterrows():
        dunning = row['dunning']

        if (gender == 'female' and dunning > 0):
            word_dict[row['term']] = dunning
        if gender == 'male' and dunning < 0:
            word_dict[row['term']] = -dunning

    print("Total tokens: {}".format(len(word_dict)))

    wc = WordCloud(background_color='white', max_font_size=300, mask=mask,
                   max_words=2000, relative_scaling=relative_scaling, min_font_size=4)
    wc.generate_from_frequencies(word_dict)
    wc.recolor(color_func=grey_color_func)


    wc.to_file(Path('data', 'plots', 'word_clouds', f'{gender}_{relative_scaling}.png'))



#
#
#
#
# class DivergenceAnalysis:
#
#     def __init__(self,
#                  c1_start_year=1980, c1_end_year=2010, c1_gender='female',
#                  c2_start_year=1980, c2_end_year=2010, c2_gender='male',
#                  percentile_score_topic=None, percentile_score_min=0, percentile_score_max=100,
#                  term_filter=None,
#                  analysis_level='topics'):
#
#         if c1_gender not in ['male', 'female', 'both'] or c2_gender not in ['male', 'female', 'both']:
#             raise ValueError('c1/c2 gender has to be male, female, or both')
#
#         self.c1_start_year = c1_start_year
#         self.c1_end_year = c1_end_year
#         self.c1_gender = c1_gender
#         self.c2_start_year = c2_start_year
#         self.c2_end_year = c2_end_year
#         self.c2_gender = c2_gender
#         self.percentile_score_topic = percentile_score_topic
#         self.percentile_score_min = percentile_score_min
#         self.percentile_score_max = percentile_score_max
#         self.analysis_level = analysis_level
#
#         self.df = pd.read_csv(Path('data', 'doc_with_outcome_and_abstract_stm.csv'),
#                          encoding='windows-1252')
#         self.df['Abstract'] = self.df['Abstract'].str.lower()
#         self.topics_str_list = [f'topic.{i}' for i in range(1, 71)]
#
#         min_year = min(c1_start_year, c2_start_year)
#         max_year = max(c1_end_year, c2_end_year)
#         self.df = self.df[(self.df.ThesisYear >= min_year) & (self.df.ThesisYear <= max_year)]
#
#
#         if percentile_score_topic:
#             self.df['percentile_score'] = self.df[f'topic.{percentile_score_topic}'].rank(pct=True) * 100 // 10 * 10
#             self.df = self.df[self.df['percentile_score'] >= self.percentile_score_min]
#             self.df = self.df[self.df['percentile_score'] <= self.percentile_score_max]
#
#         if term_filter:
#             self.df = self.df[self.df['Abstract'].str.contains(pat=term_filter, regex=True) == True]
#
#         self.df1 = self.df[(self.df.ThesisYear >= c1_start_year) & (self.df.ThesisYear <= c1_end_year)]
#         if c1_gender in ['male', 'female']:
#             self.df1 = self.df1[self.df.AdviseeGender == c1_gender]
#
#         self.df2 = self.df[(self.df.ThesisYear >= c2_start_year) & (self.df.ThesisYear <= c2_end_year)]
#         if c2_gender in ['male', 'female']:
#             self.df2 = self.df2[self.df.AdviseeGender == c2_gender]
#
#         if analysis_level == 'topics':
#             self.dtm_count_c1 = csr_matrix(self.df1[self.topics_str_list].to_numpy())
#             self.dtm_count_c2 = csr_matrix(self.df2[self.topics_str_list].to_numpy())
#             self.dtm_count_all = vstack([self.dtm_count_c1, self.dtm_count_c2])
#         else:
#
#             class LemmaTokenizer(object):
#                 def __init__(self):
#                     self.wnl = WordNetLemmatizer()
#
#                 def __call__(self, articles):
#                     return [self.wnl.lemmatize(t) for t in word_tokenize(articles, language='english')
#                             if len(t) > 2]
#             vectorizer = CountVectorizer(tokenizer=LemmaTokenizer(),
#                                               max_features=10000, stop_words='english', min_df=2)
#
#             vectorizer.fit(self.df['Abstract'].to_list())
#             self.dtm_count_all = vectorizer.transform(self.df['Abstract'].to_list())
#             self.dtm_count_c1 = vectorizer.transform(self.df1['Abstract'].to_list())
#             self.dtm_count_c2 = vectorizer.transform(self.df2['Abstract'].to_list())
#             self.vocabulary = vectorizer.vocabulary_.copy()
#             self.vocabulary_list = [x[0] for x in sorted(self.vocabulary.items(), key=lambda kv: kv[1])]
#             print('no terms in vocab', len(self.vocabulary_list))
#             for k, v in vectorizer.vocabulary_.items():
#                 self.vocabulary[v] = k
#
#
#         self.c1_name = f'{c1_start_year}-{c1_end_year}, {c1_gender}'
#         self.c2_name = f'{c2_start_year}-{c2_end_year}, {c2_gender}'
#         self.c1_name_full = self.c1_name
#         self.c2_name_full = self.c2_name
#         if self.percentile_score_topic:
#             self.c1_name_full += f' percentile score between {self.percentile_score_min}th and ' \
#              f'{self.percentile_score_max}th for {TOPIC_IDS_TO_NAME[self.percentile_score_topic]}'
#             self.c2_name_full += f' percentile score between {self.percentile_score_min}th and ' \
#              f'{self.percentile_score_max}th for {TOPIC_IDS_TO_NAME[self.percentile_score_topic]}'
#
#
#
#
#     def run_analysis(self, analysis_type='dunning', print_results=True):
#
#         if self.analysis_level == 'topics':
#             s = StatisticalAnalysis(self.dtm_count_all, self.dtm_count_c1, self.dtm_count_c2,
#                                 vocabulary=self.topics_str_list)
#         else:
#             s = StatisticalAnalysis(self.dtm_count_all, self.dtm_count_c1, self.dtm_count_c2,
#                                 vocabulary=self.vocabulary_list)
#
#         if analysis_type == 'dunning':
#             result_array, _ = s.dunning_log_likelihood()
#         elif analysis_type == 'frequency_score':
#             result_array, _ = s.frequency_score()
#             result_array = np.abs(result_array)
#         elif analysis_type == 'mann_whitney_rho':
#             result_array, _ = s.mann_whitney_rho()
#         else:
#             raise NotImplementedError(f'Analysis not implemented for {analysis_type}.')
#
#         result_array = np.array(result_array)
#         if print_results:
#             if self.analysis_level == 'topics':
#                 self.print_results_topic(result_array, analysis_type)
#             else:
#                 self.print_results_terms(result_array, analysis_type)
#
#         return result_array
#
#     def print_results_terms(self, results_array, analysis_type):
#
#         freq_scores = self.run_analysis(analysis_type='frequency_score', print_results=False)
#
#         total_terms_all = self.dtm_count_all.sum()
#         total_terms_c1 = self.dtm_count_c1.sum()
#         total_terms_c2 = self.dtm_count_c2.sum()
#
#         output =  f'Corpus 1: {self.c1_name_full}. {len(self.df1)} Theses\n'
#         output += f'Corpus 2: {self.c2_name_full}. {len(self.df2)} Theses\n\n'
#
#
#         for i in range(1,3):
#             if i == 1:
#                 output += f'Terms distinctive for {self.c1_name_full}\n'
#                 sorted_res = results_array.argsort()[::-1][:40]
#             else:
#                 output += f'Terms distinctive for {self.c2_name_full}:\n'
#                 sorted_res = results_array.argsort()[:40]
#
#             output += 'Term                  | Dunning  | Count all | {:17s}| {:17s}| ' \
#                       ' Frequency all | Freq Score | {:17s}| {:17s}'.format(
#                 self.c1_name, self.c2_name, self.c1_name, self.c2_name
#             )
#             output += '\n' + 6 * 21 * '_' + '\n'
#
#             for term_idx in sorted_res:
#                 dunning_score = results_array[term_idx]
#
# #                if freq_scores[term_idx] > 0.15 and freq_scores[term_idx] < 0.85:
# #                    continue
#                 if analysis_type == 'dunning' and ((i == 1 and dunning_score < 0) or (i == 2 and dunning_score > 0)):
#                     continue
#
#                 count_all = self.dtm_count_all[:,term_idx].sum()
#                 count_c1 = self.dtm_count_c1[:,term_idx].sum()
#                 count_c2 = self.dtm_count_c2[:,term_idx].sum()
#
#                 output += '  {:20s}| {:8.2f} |'.format(self.vocabulary[term_idx], dunning_score)
#                 output += "  {:9d}|".format(count_all)
#                 output += " {:17d}|".format(count_c1)
#                 output += " {:17d}|".format(count_c2)
#                 output += " {:14.4f}%|".format(count_all / total_terms_all * 100)
#                 output += " {:11.2f}|".format(freq_scores[term_idx])
#                 output += " {:16.4f}%|".format(count_c1 / total_terms_c1 * 100)
#                 output += " {:16.4f}%\n".format(count_c2 / total_terms_c2 * 100)
#             output += '\n\n'
#
#         print(output)
#
#
#
#     def print_results_topic(self, results_array, analysis_type):
#
#         output =  f'Corpus 1: {self.c1_name_full}. {len(self.df1)} Theses\n'
#         output += f'Corpus 2: {self.c2_name_full}. {len(self.df2)} Theses\n'
#
#         headings = ['Topic', 'ID', 'Dunning', self.c1_name, self.c2_name, 'freq overall']
#         output += f'\n{analysis_type} Results\n'
#         output += '(Interpretation: Topics at the top of the table are most distinctive'
#         output += f'for {self.c1_name}, topics at the bottom for {self.c2_name}.)\n'
#         output += ' {:49s}|'.format(headings[0])
#         for heading in headings[1:]:
#             output += ' {:19s}|'.format(heading)
#         output += '\n' + 6 * 21 * '_' + '\n'
#
#         for topic_idx in results_array.argsort()[::-1]:
#             output += '  {:48s}|  {:18s}|'.format(TOPIC_IDS_TO_NAME[topic_idx+1], str(topic_idx+1))
#             output += '  {:17.2f} |'.format(results_array[topic_idx])
#             output += ' {:16.4f}% |'.format(self.dtm_count_c1[:, topic_idx].mean() * 100)
#             output += ' {:16.4f}% |'.format(self.dtm_count_c2[:, topic_idx].mean() * 100)
#             output += ' {:16.4f}% |'.format(self.dtm_count_all[:, topic_idx].mean() * 100)
#
#             output += '\n'
#
#         output += f'\nTheses associated with the top topics for {self.c1_name_full}\n'
#         for i in range(1, 4):
#             c1_topic = results_array.argsort()[-i] + 1
#             output += f' {i}: Topic: {TOPIC_IDS_TO_NAME[c1_topic]} ({c1_topic})\n'
#             for row in self.df.sort_values(by=[f'topic.{c1_topic}'], ascending=False)[:5].iterrows():
#                 row = row[1]
#                 output += ' {:4s}|  {:8s}|  {:50s}\n'.format(str(row['ThesisYear']), row['AdviseeGender'],
#                                                                 row['ThesisTitle'])
#             output += '\n'
#
#         output += f'\nTheses associated with the top topics for {self.c2_name_full}\n'
#         for i in range(1, 4):
#             c2_topic = results_array.argsort()[i - 1] + 1
#             output += f' {i}: Topic: {TOPIC_IDS_TO_NAME[c2_topic]} ({c2_topic})\n'
#             for row in self.df.sort_values(by=[f'topic.{c2_topic}'], ascending=False)[:5].iterrows():
#                 row = row[1]
#                 output += ' {:4s}|  {:8s}|  {:50s}\n'.format(str(row['ThesisYear']), row['AdviseeGender'],
#                                                              row['ThesisTitle'])
#             output += '\n'
#
#         print(output)
#
# def plot_development_over_time(terms_or_topics_list=['topic.28', 'topic.61'], analysis_level='topics',
#                                plot_type='most_variable_topics'):
#
#
#     d = DivergenceAnalysis(
#         c1_start_year=1980, c1_end_year=2015, c1_gender='female',
#         c2_start_year=198, c2_end_year=2015, c2_gender='male',
#         analysis_level='topics',
#     )
#
#     df = d.df
#
#     terms_or_topics_list = [f'topic.{id}' for id in range(1, 71)]
# #    terms_or_topics_list = ['topic.35']
#
#     data = {}
#     annual_data = [0] * 30
#     min_freq_total = 1
#     max_freq_total = 0
#     for t in terms_or_topics_list:
#         data[t] = defaultdict(list)
#
#         for idx, year in enumerate(range(1985, 2011)):
#             time_slice = df[(df.ThesisYear >= year - 5) & (df.ThesisYear <= year + 5)]
#             freq_total = time_slice[t].mean()
#             freq_female = time_slice[time_slice.AdviseeGender == 'female'][t].mean()
#             freq_male = time_slice[time_slice.AdviseeGender == 'male'][t].mean()
#             freq_score = freq_female / (freq_female + freq_male)
#
#             data[t]['year'].append(year)
#             data[t]['freq_score'].append(freq_score)
#             data[t]['freq_total'].append(freq_total)
#
#             annual_data[idx] += abs(freq_score - 0.5)
#             if freq_total < min_freq_total:
#                 min_freq_total = freq_total
#             if freq_total > max_freq_total:
#                 max_freq_total = freq_total
#
#         data[t]['mean_freq_score'] = np.mean(data[t]['freq_score'])
#         data[t]['freq_score_range'] = max(data[t]['freq_score']) - min(data[t]['freq_score'])
#
#
#     fig = plt.figure(figsize=(12,12))
#     gs = gridspec.GridSpec(nrows=1,
#                            ncols=1,
#                            figure=fig,
#                            width_ratios=[1],
#                            height_ratios=[1],
#                            wspace=0.2, hspace=0.05
#                            )
#
#     ax = fig.add_subplot(gs[0,0])
#     ax.set_ylim(0, 1)
#     ax.set_xlim(1985, 2010)
#     ax.set_axisbelow(True)
#     ax.grid(which='major', axis='both')
#
#     dot_scaler = MinMaxScaler((1.0, 50.0))
#     dot_scaler.fit(np.array([min_freq_total, max_freq_total]).reshape(-1, 1))
#     legends = []
#
#     def draw_line(x, y, frequencies, legend):
#
# #        legends.append(legend)
#         x_spline = np.linspace(min(x), max(x), (2010 - 1985 + 1) * 1000)
#         spl = make_interp_spline(x, y, k=3)  # BSpline object
#         y_spline = spl(x_spline)
#
#         line_interpolater = interp1d(x, frequencies)
#         line_widths = line_interpolater(x_spline)
#         line_widths = dot_scaler.transform(line_widths.reshape(-1, 1)).flatten()
#
#         color = sns.color_palette()[len(legends)]
#         ax.scatter(x_spline, y_spline, s=line_widths, antialiased=True,
#                    color=color)
#         legends.append(mpatches.Patch(color=color, label=legend))
#
#     if plot_type == 'most_divergent_topics':
#         ax.set_title(f'Most divergent topics for female (top) and male authors (bottom)',
#                         weight='bold', fontsize=18)
#         sorted_items = sorted(data.items(), key = lambda k_v: k_v[1]['mean_freq_score'], reverse=True)
#         for t, t_data in sorted_items[:4] + sorted_items[::-1][:4]:
#             y = t_data['freq_score']
#             x = t_data['year']
#             freqs = t_data['freq_total']
#             legend = TOPIC_IDS_TO_NAME[int(t[6:])]
#             draw_line(x, y, freqs, legend)
#
#     elif plot_type == 'most_variable_topics':
#         ax.set_title(f'Most variable topics',
#                         weight='bold', fontsize=18)
#         sorted_items = sorted(data.items(), key = lambda k_v: k_v[1]['freq_score_range'], reverse=True)
#         for t, t_data in sorted_items[:5]:
#             y = t_data['freq_score']
#             x = t_data['year']
#             freqs = t_data['freq_total']
#             legend = TOPIC_IDS_TO_NAME[int(t[6:])]
#
#             draw_line(x, y, freqs, legend)
#
#
#     ax.legend(handles=legends, loc=4)
# #    ax.plot([1985, 2010], [0.5, 0.5], 'k-', lw=2)
#     print(min_freq_total, max_freq_total)
#
#     plt.show()

#def draw_interpolated_line()


if __name__ == '__main__':
    # d = DivergenceAnalysis(
    #     c1_start_year=2000, c1_end_year=2010, c1_gender='both',
    #     c2_start_year=2010, c2_end_year=2020, c2_gender='both'
    # )
    # d.run_analysis(analysis_type='dunning')
    #

#    wordcloud()

    # d = Dataset()
    # c1 = d.copy().filter(institution_filter='princeton')
    # c2 = d.copy().filter(institution_filter='not_princeton')
    # divergence_analysis(d, c1, c2)



    # d = Dataset()
    # c1 = d.copy().filter(advisor_gender='male')
    # c2 = d.copy().filter(advisor_gender='female')
    # divergence_analysis(d, c1, c2)

    # d = Dataset()
    # d.filter(advisor_gender='female')
    # c1 = d.copy().filter(author_gender='female')
    # c2 = d.copy().filter(author_gender='male')
    # divergence_analysis(d, c1, c2, topics_or_terms='topics')

#     d = Dataset()
#     d.filter(author_gender='male', start_year=1976, end_year=1999)
#     c1 = d.copy().filter(advisor_gender='female')
#     c2 = d.copy().filter(advisor_gender='male')
# #    c1.normalize_dataset_by_5year_interval()
# #    c2.normalize_dataset_by_5year_interval()
#     divergence_analysis(d, c1, c2, topics_or_terms='terms',
#                         c1_name='female advisor', c2_name='male advisor')
#     divergence_analysis(d, c1, c2, topics_or_terms='topics',
#                         c1_name='female advisor', c2_name='male advisor')

    # Loads the entire dataset of dissertations
    d = Dataset()
    d.topic_percentile_score_filter(24, min_percentile_score=80)
#    d.filter(author_gender='male', start_year=2000, end_year=2015)
#    d.filter(term_filter='race')

#
    # Create two sub-datasets, one for female authors and one for male authors
    c1 = d.copy().filter(author_gender='female')
    c2 = d.copy().filter(author_gender='male')

    # divergence_analysis(d, c1, c2, c1_name='female author', c2_name='male author',
    #                     topics_or_terms='terms', sort_by='frequency_score',
    #                     number_of_terms_to_print=80)



    divergence_analysis(d, c1, c2, topics_or_terms='topics',
                        c1_name='female', c2_name='male', sort_by='dunning')

    c1.print_dissertations_mentioning_terms_or_topics()

    # r = d.copy().filter(term_filter='gender')
    # divergence_analysis(d, d, r, topics_or_terms='topics',
    #                     c1_name='not race', c2_name='race')


    # divergence_analysis(d, c1, c2)

    # networks generated with correlation
    # maybe better: use co-use of topics -> get topic-overlap matrix, i.e. to what degree are
    # topics co-used.
    # stemmer: integrated in STM R package.

