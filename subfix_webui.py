import argparse
import json
import os

import librosa
import gradio as gr
import numpy as np
import soundfile

g_json_key_text = ""
g_json_key_path = ""
g_source_json = ""
g_target_json = ""

g_max_json_index = 0
g_index = 0
g_batch = 10
g_text_list = []
g_audio_list = []
g_checkbox_list = []
g_data_json = []


def reload_data(index, batch):
    global g_index
    g_index = index
    global g_batch 
    g_batch = batch
    datas = g_data_json[index:index+batch]
    output = []
    for d in datas:
        output.append(
            {
                g_json_key_text: d[g_json_key_text],
                g_json_key_path: d[g_json_key_path]
            }
        )
    return output


def b_change_index(index, batch):
    global g_index, g_batch
    g_index, g_batch = index, batch
    datas = reload_data(index, batch)
    output = []
    for _ in datas:
        output.append(_[g_json_key_text])
    for _ in range(10 - len(datas)):
        output.append(None)
    for _ in datas:
        output.append(_[g_json_key_path])
    for _ in range(10 - len(datas)):
        output.append(None)
    for _ in range(10):
        output.append(False)
    return output


def b_next_index(index, batch):
    if (index + batch) <= g_max_json_index:
        return index + batch , *b_change_index(index + batch, batch)
    else:
        return index, *b_change_index(index, batch)


def b_previous_index(index, batch):
    if (index - batch) >= 0:
        return index - batch , *b_change_index(index - batch, batch)
    else:
        return index, *b_change_index(0, batch)


def b_submit_change(*text_list):
    global g_data_json
    for i, new_text in enumerate(text_list):
        if g_index + i <= g_max_json_index:
            new_text = new_text.strip()+' '
            g_data_json[g_index + i][g_json_key_text] = new_text
    return g_index, *b_change_index(g_index, g_batch)


def b_delete_audio(*checkbox_list):
    global g_data_json

    for i, checkbox in reversed(list(enumerate(checkbox_list))):
        if g_index + i < len(g_data_json):
            if (checkbox == True):
                g_data_json.pop(g_index + i)
    return g_index, *b_change_index(g_index, g_batch)


def b_merge_audio(interval_r, *checkbox_list):
    global g_data_json
    checked_index = []
    audios_path = []
    audios_text = []
    for i, checkbox in enumerate(checkbox_list):
        if (checkbox == True and g_index+i < len(g_data_json)):
            checked_index.append(g_index + i)
            
    if (len(checked_index)>1):
        for i in checked_index:
            audios_path.append(g_data_json[i][g_json_key_path])
            audios_text.append(g_data_json[i][g_json_key_text])
        for i in reversed(checked_index[1:]):
            g_data_json.pop(i)

        base_index = checked_index[0]
        base_path = audios_path[0]
        g_data_json[base_index][g_json_key_text] = "".join(audios_text)

        audio_list = []
        l_sample_rate = None
        for i, path in enumerate(audios_path):
            data, sample_rate = librosa.load(path, sr=l_sample_rate, mono=True)
            l_sample_rate = sample_rate
            if (i > 0):
                silence = np.zeros(int(l_sample_rate * interval_r))
                audio_list.append(silence)

            audio_list.append(data)

        audio_concat = np.concatenate(audio_list)

        soundfile.write(base_path, audio_concat, l_sample_rate)

        b_save_json()

    return g_index, *b_change_index(g_index, g_batch)


def b_save_json():
    with open(g_target_json,'w', encoding="utf-8") as file:
        for data in g_data_json:
            file.write(f'{json.dumps(data, ensure_ascii = False)}\n')


def set_global(source_json, target_json, json_key_text, json_key_path):
    global g_json_key_text, g_json_key_path, g_source_json, g_target_json
    
    assert(source_json != "None")

    if (target_json == "None"):
        target_json = source_json

    g_source_json = source_json
    g_target_json = target_json
    g_json_key_text = json_key_text
    g_json_key_path = json_key_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--source_json', default="None", help='source file xxx.json')
    parser.add_argument('--target_json', default="None", help='target file xxx.json will be save')
    parser.add_argument('--json_key_text', default="text", help='the text key name in json, maybe is text')
    parser.add_argument('--json_key_path', default="wav_path", help='the path key name in json, maybe is wav_path')

    args = parser.parse_args()

    set_global(args.source_json, args.target_json, args.json_key_text, args.json_key_path)

    with open(g_source_json, 'r', encoding="utf-8") as file:
        g_data_json = file.readlines()
        g_data_json = [json.loads(line) for line in g_data_json]
        g_max_json_index = len(g_data_json)-1
    
    with gr.Blocks() as demo:

        with gr.Row():
            index_slider = gr.Slider(
                    minimum=0, maximum=g_max_json_index, value=g_index, step=1, label="Index", scale=4
            )
            batchsize_slider = gr.Slider(
                    minimum=1, maximum=10, value=g_batch, step=1, label="Batch Size", scale=2, interactive=False
            )
            interval_slider = gr.Slider(
                    minimum=0, maximum=2, value=0, step=0.01, label="Interval", scale=2
            ) 

        with gr.Row():
            with gr.Column():
                for _ in range(0,10):
                    with gr.Row():
                        text = gr.Textbox(
                            label = "Text",
                            visible = True,
                            scale=5
                        )
                        audio_output = gr.Audio(
                            label="Output Audio",
                            visible = True,
                            scale=5
                        )
                        audio_check = gr.Checkbox(
                            label="Yes",
                            show_label = True,
                            info = "Choose Audio",
                            scale=1
                        )
                        g_text_list.append(text)
                        g_audio_list.append(audio_output)
                        g_checkbox_list.append(audio_check)
    
        with gr.Row():
            btn_change_index = gr.Button("Change Index")
            btn_submit_change = gr.Button("Submit Change")
            btn_merge_audio = gr.Button("Merge Audio")
            btn_delete_audio = gr.Button("Delete Audio")
            btn_previous_index = gr.Button("Previous Index")
            btn_next_index = gr.Button("Next Index")
            
        with gr.Row():
            btn_save_json = gr.Button("Save json")

        btn_change_index.click(
            b_change_index,
            inputs=[
                index_slider,
                batchsize_slider,
            ],
            outputs=[
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ],
        )

        
        btn_submit_change.click(
            b_submit_change,
            inputs=[
                *g_text_list,
            ],
            outputs=[
                index_slider,
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ],
        )

        btn_previous_index.click(
            b_previous_index,
            inputs=[
                index_slider,
                batchsize_slider,
            ],
            outputs=[
                index_slider,
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ],
        )
        
        btn_next_index.click(
            b_next_index,
            inputs=[
                index_slider,
                batchsize_slider,
            ],
            outputs=[
                index_slider,
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ],
        )

        btn_delete_audio.click(
            b_delete_audio,
            inputs=[
                *g_checkbox_list
            ],
            outputs=[
                index_slider,
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ]
        )

        btn_merge_audio.click(
            b_merge_audio,
            inputs=[
                interval_slider,
                *g_checkbox_list
            ],
            outputs=[
                index_slider,
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ]
        )

        btn_save_json.click(
            b_save_json
        )

        demo.load(
            b_change_index,
            inputs=[
                index_slider,
                batchsize_slider,
            ],
            outputs=[
                *g_text_list,
                *g_audio_list,
                *g_checkbox_list
            ],
        )
        
    demo.launch()