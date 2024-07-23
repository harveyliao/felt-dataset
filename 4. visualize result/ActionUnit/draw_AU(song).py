import logging
import os
import io
import imageio.v2 as imageio
import numpy as np
from feat.utils.io import read_feat
from feat.plotting import plot_face
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from multiprocessing import Pool

# Setup logging
logging.basicConfig(filename='draw_au.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# Configuration
csv_path = "F:/smoothed/"
video_path = "F:/video/ActionUnit/"
start_actor_num = 1
end_actor_num = 25
isSong = False
num_processes = 10 # adjust this according to host machine performance

# Overlay video settings
DPI = 100

def generate_au_plot_figures(input_prediction):
    """Generate an array of Action Unit (AU) plot figures from a feat dataframe.

    This function takes a feat dataframe containing Action Unit data and generates
    a plot for each frame using the plot_face function. It handles potential
    ValueErrors and logs any frames that cause errors.

    :param input_prediction: A feat dataframe containing Action Unit data
    :return figs: A list of figures for each successfully plotted frame
    :return error_frames: A list of frame number that causes error

    """
    figs = []

    total_frames = input_prediction.aus.shape[0]
    error_frames = []

    for frame in range(total_frames):
        try:
            aus = np.array(input_prediction.aus.iloc[frame])
            muscles = {'all': 'heatmap'}
            ax = plot_face(au=aus, muscles=muscles, title=f'Frame {frame}')
            fig = ax.get_figure()
            figs.append(fig) # append new frame to figs list
        except ValueError as e:
            logging.warning(f"ValueError encountered at frame {frame}: {e}")
            error_frames.append(frame)

    logging.warning(f"There are {len(error_frames)} frames that raised ValueError: {error_frames}")

    return (figs, error_frames)

def generate_au_video_from_csv(args):
    """Generate an Action Unit (AU) video from a CSV feat dataframe.

    :param args: A tuple containing two variables: 
        - smoothed_csv_path: path of the smoothed CSV file
        - au_video_path: path where the AU video is saved to

    """
    smoothed_csv_path, au_video_path = args

    # if the target file exists, then skip it since it has been processed. Othrewise proceed
    if os.path.exists(au_video_path):
        logging.info(f"File {au_video_path} already processed, skipping.")
        return

    video_prediction = read_feat(smoothed_csv_path)
    logging.info(f"Successfully loaded file: {smoothed_csv_path}, now generating overlay for each frame")
    
    figs, _ = generate_au_plot_figures(video_prediction)
    writer = imageio.get_writer(au_video_path, fps=30, codec='libx264', format='FFMPEG', macro_block_size=None)

    logging.info("generating video from frames")
    for fig in figs:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=DPI)
        buf.seek(0)
        image = imageio.imread(buf)
        writer.append_data(image)
        buf.close()
        plt.close(fig)

    writer.close()
    logging.info(f'Video saved as {au_video_path}')

def main():
    tasks = [] # multiprocessing pool

    for i in range(start_actor_num, end_actor_num):
        if i == 18 and isSong:
            continue
        folder_name = f"Actor_{i:02}" 
        smoothed_csv_folder_path = os.path.join(csv_path, folder_name)
        au_video_folder_path = os.path.join(video_path, folder_name)

        if not os.path.exists(au_video_folder_path):
            os.makedirs(au_video_folder_path)
            logging.info(f"Created folder {au_video_folder_path}")
        
        for file_name in os.listdir(smoothed_csv_folder_path):
            smoothed_csv_path = os.path.join(smoothed_csv_folder_path, file_name)
            video_basename = os.path.splitext(os.path.basename(smoothed_csv_path))[0]
            au_video_path = os.path.join(au_video_folder_path, f"{video_basename}.mp4")
            
            tasks.append((smoothed_csv_path, au_video_path))

    with Pool(processes=num_processes) as pool:
        pool.map(generate_au_video_from_csv, tasks)

if __name__ == '__main__':
    main()
