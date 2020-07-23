"""
    Create by: apenasrr
    Source: https://github.com/apenasrr/
    
    Create automatic descriptions with a several timestamp link, 
    of a video composed by the joining of several small videos
    
    The required spreadsheet is automatically generated 
    by the app mass_videojoin: https://github.com/apenasrr/mass_videojoin
"""

import pandas as pd
import subprocess
import datetime
import time
import os 


def get_length(filename):

    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", 
                             filename],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT)
    
    return float(result.stdout)

    
def get_duration_video(path_file):
  
    duration_sec = get_length(path_file)
    duration_delta = datetime.timedelta(seconds=duration_sec)
    print(path_file, '\n', f'Duration: {duration_delta}', '\n')
    duration_delta_micro = \
        datetime.timedelta(microseconds=duration_delta.microseconds)
    duration_format = duration_delta - duration_delta_micro
    
    return duration_format


def include_timestamp(df):
    """
    :input: DataFrame. df. Columns required: file_output, duration_new
    :return: DataFrame.
    """

    def include_head_file_mark(df):

        df['head_file'] = ''
        for index, row in df.iterrows():
            if index == 0:
                head_file = True
            else:
                head_file = df.loc[index-1, 'file_output'] != \
                            df.loc[index, 'file_output']
            df.loc[index, 'head_file'] = head_file
        
        return df
        
    df = include_head_file_mark(df)
    df['duration_new'] = pd.to_timedelta(df['duration_new'], unit='D')
    df['time_stamp'] = datetime.timedelta(seconds=0)
    for index, row in df.iterrows():
        if index == 0:
            pass
        else:
            if df.loc[index,'head_file']:
                pass
            else:
                time_stamp = df.loc[index-1,'duration_new'] + \
                             df.loc[index-1,'time_stamp']
                df.loc[index, 'time_stamp'] = time_stamp

    return df


def timedelta_to_string(timestamp):
    
    timestamp_micro = datetime.timedelta(microseconds=timestamp.microseconds)
    timestamp = timestamp - timestamp_micro
    hou, min_full = divmod(timestamp.seconds, 3600)
    min, sec = divmod(min_full, 60)
    timestamp = '%02d:%02d:%02d' % (hou, min, sec)
    
    return timestamp


def get_file_name_without_extension(file_name):
    file_name_without_extension = os.path.splitext(file_name)[0]
    return file_name_without_extension


def sequencer_file_repeated(df, column_name):

    def to_down(df, column_name, new_column, index):
        actual = df.loc[index, column_name]
        after = df.loc[index + 1, column_name]
        if actual == after:
            df.loc[index, new_column] = actual + '_P01'
        else:
            df.loc[index, new_column] = actual
        return df
    
    def to_up_down(df, column_name, new_column, index, count):
        
        before = df.loc[index - 1, column_name]
        actual = df.loc[index, column_name]
        after = df.loc[index + 1, column_name]
        if actual == after:
            if before != actual:
                count = 1
            df.loc[index, new_column] = actual + '_P%02d' % count    
        else:
            if before == actual:
                df.loc[index, new_column] = actual + '_P%02d' % count
            else:
                df.loc[index, new_column] = actual
        return df, count

    def to_up(df, column_name, new_column, index, count):
        
        before = df.loc[index - 1, column_name]
        actual = df.loc[index, column_name]
        if before == actual:
            df.loc[index, new_column] = actual + '_P%02d' % count
        else:
            df.loc[index, new_column] = actual
        return df
        
    new_column = column_name + '_seq'
    count = 1
    size_lines = df.shape[0]
    if size_lines > 1:
        for index, row in df.iterrows():
            if index == 0:            
                df = to_down(df, column_name, new_column, index)
                count += 1
            else:
                if index+1 < size_lines:
                    df, count = to_up_down(df, column_name, new_column, 
                                           index, count)
                    count += 1
                else:
                    df = to_up(df, column_name, new_column, index, count)

    return df

    
def create_df_description_without_folder(df):
    
    # create column time_stamp_str
    df['time_stamp'] = pd.to_timedelta(df['time_stamp'], unit='D')
    df['time_stamp_str'] = df['time_stamp'].apply(timedelta_to_string)
    
    # Of column file_name_origin remove extension
    df['file_name_origin'] = \
        df['file_name_origin'].apply(get_file_name_without_extension)
    
    # input sequencer for repeated file_name_origin
    ## In case of split origin files, will be different output files 
    ##  with the same source file name. 
    ##  In this case, it is necessary to differentiate the name of the source 
    ##  files in the timestamp, through a numeric sequence. 
    ##  e.g.: filename_P01, filename_P02
    df = sequencer_file_repeated(df, 'file_name_origin')

    # create dataframe description as df_output
    df_output = df.copy()
    df_output = df_output.loc[:, ['file_name_origin', 'file_output', 
                                  'duration_new', 'head_file']]
    df_output = df_output.drop_duplicates(subset='file_output', keep='first')
    df_output['description'] = ''
    for index, row in df_output.iterrows():
        file_output = row['file_output']
        mask_file_output = df['file_output'].isin([file_output])
        df_video_details = df.loc[mask_file_output, 
                                  ['file_name_origin_seq', 'time_stamp_str']]
        df_video_details = df_video_details.reset_index()
        description = ''
        for index2, row in df_video_details.iterrows():
            file_name_origin_seq = row['file_name_origin_seq']
            
            if index2 == 0:
                description = row['time_stamp_str'] + ' ' +\
                              file_name_origin_seq
            else:
                description = description + '\n' + row['time_stamp_str'] + \
                              ' ' + file_name_origin_seq
        df_output.loc[index, 'description'] = description
        
    df_output = df_output.reindex(['file_output', 'description'], axis=1)
    
    return df_output


def create_df_description_with_folder(df):
    
    # create column time_stamp_str
    df['time_stamp'] = pd.to_timedelta(df['time_stamp'], unit='D')
    df['time_stamp_str'] = df['time_stamp'].apply(timedelta_to_string)

    
    # creat list with cols folders names
    cols_folders_start = list(df.columns).index('time_stamp') + 1
    cols_folders_finish = list(df.columns).index('time_stamp_str')
    cols_folders = list(df.columns)[cols_folders_start:cols_folders_finish]

    # TODO consolidate cols_folders in a unique column 
    
    # Of column file_name_origin remove extension
    df['file_name_origin'] = \
        df['file_name_origin'].apply(get_file_name_without_extension)
    
    # input sequencer for repeated file_name_origin
    ## In case of split origin files, will be different output files 
    ##  with the same source file name. 
    ##  In this case, it is necessary to differentiate the name of the source 
    ##  files in the timestamp, through a numeric sequence. 
    ##  e.g.: filename_P01, filename_P02
    df = sequencer_file_repeated(df, 'file_name_origin')
    
    # create dataframe description as df_output
    df_output = df.copy()
    cols_keep = ['file_name_origin', 'file_output', 
                 'duration_new', 'head_file']
    df_output = df_output.loc[:, cols_keep]
    df_output = df_output.drop_duplicates(subset='file_output', keep='first')
    df_output['description'] = ''
    df_output['warning'] = ''
    for index, row in df_output.iterrows():
        file_output = row['file_output']
        mask_file_output = df['file_output'].isin([file_output])
        cols_df_video_details = ['file_name_origin_seq', 'time_stamp_str'] + \
                                cols_folders
        df_video_details = df.loc[mask_file_output, cols_df_video_details]
        df_video_details = df_video_details.reset_index()
        
        description = ''
        # list of folders origin from the output file
        col_folder = cols_folders[0]
        list_folders = list(df_video_details[col_folder].unique())
        
        for index_folder, folder in enumerate(list_folders):
            mask_folder = df_video_details[col_folder].isin([folder])
            df_video_detail_folder = df_video_details.loc[mask_folder, :]
            if index_folder == 0:
                description = folder
            else:
                description = description + '\n\n' + folder
                
            for index2, row in df_video_detail_folder.iterrows():
                file_name_origin_seq = row['file_name_origin_seq']
                description = description + '\n' + row['time_stamp_str'] + \
                              ' ' + file_name_origin_seq   
        # check for size char limit in description
        if len(description) > 1000:
            df_output.loc[index, 'warning'] = 'max size reached'
        else:
            pass
        df_output.loc[index, 'description'] = description
                
    df_output = df_output.reindex(['file_output', 'description', 'warning'], 
                                  axis=1)
                                  
    return df_output
        


def implant_hashtag_blocks(df, keyword):
    
    df = df.reset_index(drop=True)
    for index, row in df.iterrows():
        description = row['description']
        df.loc[index, 'description'] = \
            f'#{keyword}%02d\n\n{description}' % (index + 1)
    return df
    
    
def get_summary_mid_without_folder(df, keyword):
    
    size = df.shape[0]
    mid = ''
    for index in range(size):
        if index == 0:
            mid = f'#{keyword}%02d' % (index + 1)
        else:
            mid = f'{mid}\n#{keyword}%02d' % (index + 1)
            
    return mid
    
    
    
def create_summary():
    
    summary_top_content = get_txt_content(file_path='summary_top.txt')

    df = pd.read_excel('video_details.xlsx')
    df = include_cols_folders_structure(df)

    # summary_mid_content = get_summary_mid_without_folder(df, keyword='Bloco')
    summary_mid_content = get_summary_mid_with_folder(df, keyword='Bloco')
    
    summary_bot_content = get_txt_content(file_path='summary_bot.txt')
    
    summary_content = summary_top_content + '\n' + \
                      summary_mid_content + '\n' + \
                      summary_bot_content
    
    create_txt(file_path='summary.txt', stringa=summary_content)
    


    
def get_txt_content(file_path):
    
    file = open(file_path,'r', encoding='utf-8')
    file_content = file.readlines()
    file_content = ''.join(file_content)
    file.close()
    return file_content


def create_txt(file_path, stringa):

    f = open(file_path, "w", encoding='utf8')
    f.write(stringa)
    f.close()


def remove_root_folders(df, skip_cols):
    
    len_cols = len(df.columns)
    list_n_col_to_delete = []
    for n_col in range(skip_cols, len_cols-1):
        serie = df.iloc[:, n_col]
        # check for column with more than 1 unique value (folder root)
        col_has_one_unique_value = check_col_unique_values(serie)
        if col_has_one_unique_value:
            name_col = df.columns[n_col]
            list_n_col_to_delete.append(name_col)

    df = df.drop(list_n_col_to_delete, axis=1)
    
    return df
    

def get_summary_mid_with_folder(df, keyword):
    """
    Create text marking the output files and informing the folder structure
        that originate each one
    :return: String.
    """
    
    def get_dict_file_folders(list_file_output, df_folder):
        """
        :list_file_output: List.
        :df_folder: DataFrame. Must contain column 'file_output'
        :return: list of dict, containing all origin folders of each file_output
        """
    
        def get_list_folders_from_file_output(file_output, df_folder):
            """
            :file_output: String.
            :df_folder: DataFrame. Must contain column 'file_output'
            :return: list. All origin folders of a file_output
            """
            
            mask_file_output = df_folder['file_output'].isin([file_output])
            
            
            # they are to the right of the column 'file_output'
            # col_qt = len(df_folder.columns)
            col_number = list(df_folder.columns).index('file_output') + 1
            # TODO iterate from col all cols of folders [col_number:]
            col_name = df_folder.columns[col_number]
            serie_file_folder = df_folder.loc[mask_file_output, col_name]
            list_file_folder = serie_file_folder.unique().tolist()
            
            return list_file_folder
        
        dict_file_folder = {}
        # iterate for each file_output, looking for their corresponding source 
        #  folders in df_folder
        for file_output in list_file_output:
            list_folders_file_output = \
                get_list_folders_from_file_output(file_output, df_folder)
            dict_file_folder[file_output] = list_folders_file_output
        
        return dict_file_folder

    def get_summary_mid_content_with_folders(list_file_output, 
                                             dict_file_folders):
        
        mid = ''
        for index, file_output in enumerate(list_file_output, 1):
            list_folders = dict_file_folders[file_output]
            str_folders = '\n'.join(list_folders)
            str_mark = f'#{keyword}%02d' % (index)
            if index == 1:
                mid = str_folders + '\n' + str_mark
            else:
                mid = mid + '\n\n' + str_folders + '\n' + str_mark
        return mid
        
    # get file_output unique values
    list_file_output = df['file_output'].unique()
    dict_file_folders = get_dict_file_folders(list_file_output, df)
        
    summary_mid_content = \
        get_summary_mid_content_with_folders(
            list_file_output=list_file_output, 
            dict_file_folders=dict_file_folders)

    return summary_mid_content
    

def include_cols_folders_structure(df):
    """
    Includes to the right of the DataFrame, columns corresponding to each
     depth level of the folder structure of the origin files
    :df: DataFrame. Requires column 'file_folder_origin'
    """
    
    skip_cols = len(df.columns)
    df_folder = df['file_folder_origin'].str.split('\\', expand=True)
    df_folder = df.merge(df_folder, left_index=True, right_index=True)
    # remove root folders columns (dont change along the files)
    df_folder = remove_root_folders(df_folder, skip_cols=skip_cols)
    
    return df_folder

            
def check_col_unique_values(serie):
    
    serie_unique = serie.drop_duplicates(keep='first')
    list_unique_values = serie_unique.unique().tolist()
    qt_unique_values = len(list_unique_values)
    if qt_unique_values == 1:
        return True
    else:
        return False
        

def get_df_source():
    
    df_source = pd.read_excel('video_details.xlsx')
    
    list_columns_keep = ['file_folder', 'file_name', 'file_folder_origin', 
                         'file_name_origin', 'file_output']
    
    df = df_source.loc[:, list_columns_keep]
    
    return df
    
    
def main():
    """
    Requeriments: Spreadsheet named 'video_details.xlsx' with columns:
                    ['file_folder', 'file_name', 'file_folder_origin', 
                     'file_name_origin', 'file_output']
                     
    The required spreadsheet is automatically generated 
    by the app mass_videojoin: https://github.com/apenasrr/mass_videojoin
    """

    
    def add_column_filepath(df):
        
        df['file_path'] = df['file_folder'] + '\\' + df['file_name']
        
        return df
        
    def add_column_duration(df):
        
        df['duration_new'] = df['file_path'].apply(get_duration_video)
        
        return df
   
    df = get_df_source()
    df = add_column_filepath(df)
    df = add_column_duration(df)
    df = include_timestamp(df)
    df = include_cols_folders_structure(df)
   
    # df_description = create_df_description_without_folder(df)
    df_description = create_df_description_with_folder(df)
    
    # input hashtag to mark blocks
    df_description = implant_hashtag_blocks(df_description, 'Bloco')
    
    df_description.to_excel('list.xlsx', index=False)
    
    # create summary.txt
    create_summary()
    
    # TODO feature to expose folder hierarchies more than one level deep
    
    
main()