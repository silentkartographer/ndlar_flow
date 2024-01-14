################################################################################
##                                                                            ##
##    CONTAINS: Script to create plots describing data/MC metrics             ##
##              events using a dictionary                                     ##
##                                                                            ##
################################################################################

import matplotlib.pyplot as plt
import numpy as np
import particlePDG_defs as pdg_defs

def plot_event_hit_summ_metrics(d, is_mc):

    if is_mc:
        mc_title = '[Simulation]'
        sample_type = "MC"
    else:
        mc_title = '[Data]'
        sample_type = "Data"

    sel_pdg = np.unique([d[key]['event_pdg'] for key in d.keys()])
    hits_dsets = np.unique([d[key]['hits_dset'] for key in d.keys()])
    alpha_options = [1.0, 0.8]
    color_options = ['#4daf4a', '#ff7f00']
    linestyle_options = ['--', '-']
    linewidth_options = [1.5, 1.5]
    fill_options = [False, False]
    print("hits_dsets:",hits_dsets)

    # PLOT: total charge in an event
    fig0, ax0 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data0 = np.array([d[key]['total_charge'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts0, bins0 = np.histogram(data0, bins=np.linspace(0,20000,21))
            ax0.hist(bins0[:-1], bins=bins0, weights = counts0, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax0.set_xlabel('Total Charge [ke-]')
    ax0.set_ylabel('Count / 1000 ke-')
    ax0.set_title(r'Total Charge Per Selected Event '+mc_title)
    ax0.legend()
    plt.savefig(sample_type+"_selected_events_total_charge.png")
    plt.close(fig0)

    # PLOT: number of hits in an event
    fig1, ax1 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data1 = np.array([d[key]['num_hits'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts1, bins1 = np.histogram(data1, bins=np.linspace(0,500,26))
            ax1.hist(bins1[:-1], bins=bins1, weights = counts1, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax1.set_xlabel('Number of Hits')
    ax1.set_ylabel('Event Count / 20 Hits')
    ax1.set_title(r'Number of Hits Per Selected Event '+mc_title)
    ax1.legend()
    plt.savefig(sample_type+"_selected_events_total_hits_per_event.png")
    plt.close(fig1)


    # PLOT: number of separate pixels triggered in an event
    fig2, ax2 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg: 
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data2 = np.array([d[key]['num_channels'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts2, bins2 = np.histogram(data2, bins=np.linspace(0,100,21))
            ax2.hist(bins2[:-1], bins=bins2, weights = counts2, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset,\
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax2.set_xlabel('Number of Unique Channels Triggered')
    ax2.set_ylabel('Event Count / 20 Channels')
    ax2.set_title("Number of Unique Channels Triggered \nPer Selected Event "+mc_title)
    ax2.legend()
    plt.savefig(sample_type+"_selected_events_total_unique_channels_per_event.png")
    plt.close(fig2)

    return

def plot_channel_metrics(d, is_mc):

    if is_mc:
        mc_title = '[Simulation]'
        sample_type = "MC"
    else:
        mc_title = '[Data]'
        sample_type = "Data"

    sel_pdg = np.unique([d[key]['event_pdg'] for key in d.keys()])
    hits_dsets = np.unique([d[key]['hits_dset'] for key in d.keys()])
    alpha_options = [1.0, 0.8]
    color_options = ['#4daf4a', '#ff7f00']
    linestyle_options = ['--', '-']
    linewidth_options = [1.5, 1.5]
    fill_options = [False, False]

    # PLOT: hits per channel per event
    fig0, ax0 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data0 = np.array([d[key]['hit_mult'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts0, bins0 = np.histogram(data0, bins=np.linspace(0,10,11))
            ax0.hist(bins0[:-1], bins=bins0, weights = counts0, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax0.set_xlabel('Hit Multiplicity / Channel / Event')
    ax0.set_ylabel('Channel Count / Hit')
    ax0.set_title(r'Hit Multiplicity Per Channel in Selected Events '+mc_title)
    ax0.legend()
    plt.savefig(sample_type+"_selected_events_hits_per_channel_per_event.png")
    plt.close(fig0)

    # PLOT: max hit amplitude per channel per event
    fig1, ax1 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data1 = np.array([d[key]['max_hit_amp'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts1, bins1 = np.histogram(data1, bins=np.linspace(0,200,41))
            ax1.hist(bins1[:-1], bins=bins1, weights = counts1, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax1.set_xlabel('Max Hit Amplitude / Channel / Event [ke-]')
    ax1.set_ylabel('Channel Count / 5 ke-')
    ax1.set_title(r'Maximum Hit Amplitiude Per Channel in Selected Events '+mc_title)
    ax1.legend()
    plt.savefig(sample_type+"_selected_events_max_hit_amp_per_channel_per_event.png")
    plt.close(fig1)

    # PLOT: min hit amplitude per channel per event
    fig2, ax2 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data2 = np.array([d[key]['min_hit_amp'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts2, bins2 = np.histogram(data2, bins=np.linspace(0,200,41))
            ax2.hist(bins2[:-1], bins=bins2, weights = counts2, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax2.set_xlabel('Min Hit Amplitude / Channel / Event [ke-]')
    ax2.set_ylabel('Channel Count / 5 ke-')
    ax2.set_title(r'Minimum Hit Amplitiude Per Channel in Selected Events '+mc_title)
    ax2.legend()
    plt.savefig(sample_type+"_selected_events_min_hit_amp_per_channel_per_event.png")
    plt.close(fig2)

    # PLOT: first hit amplitude per channel per event
    fig3, ax3 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data3 = np.array([d[key]['first_hit_amp'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts3, bins3 = np.histogram(data3, bins=np.linspace(0,200,41))
            ax3.hist(bins3[:-1], bins=bins3, weights = counts3, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax3.set_xlabel('First Hit Amplitude / Channel / Event [ke-]')
    ax3.set_ylabel('Channel Count / 5 ke-')
    ax3.set_title(r'First Hit Amplitiude Per Channel in Selected Events '+mc_title)
    ax3.legend()
    plt.savefig(sample_type+"_selected_events_first_hit_amp_per_channel_per_event.png")
    plt.close(fig3)

    # PLOT: last hit amplitude per channel per event
    fig4, ax4 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data4 = np.array([d[key]['last_hit_amp'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts4, bins4 = np.histogram(data4, bins=np.linspace(0,200,41))
            ax4.hist(bins4[:-1], bins=bins4, weights = counts4, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax4.set_xlabel('Last Hit Amplitude / Channel / Event [ke-]')
    ax4.set_ylabel('Channel Count / 5 ke-')
    ax4.set_title(r'Last Hit Amplitiude Per Channel in Selected Events '+mc_title)
    ax4.legend()
    plt.savefig(sample_type+"_selected_events_last_hit_amp_per_channel_per_event.png")
    plt.close(fig4)
    
    # PLOT: first/last hit delta(t) per channel per event
    fig4, ax4 = plt.subplots(figsize=(6,4))
    for pdg in sel_pdg:
        for hits_dset in hits_dsets:
            idx = hits_dsets.tolist().index(hits_dset)
            data4 = np.array([d[key]['first_last_hit_delta_t'] for key in d.keys() if d[key]['event_pdg']==pdg and d[key]['hits_dset']==hits_dset])
            counts4, bins4 = np.histogram(data4, bins=np.linspace(0,20,41))
            ax4.hist(bins4[:-1], bins=bins4, weights = counts4, \
                     label=pdg_defs.selection_pdg_dict[pdg]+", "+hits_dset, \
                     linewidth=linewidth_options[idx], alpha=alpha_options[idx], \
                     color=color_options[idx], edgecolor=color_options[idx], \
                     linestyle=linestyle_options[idx], fill = fill_options[idx])
    ax4.set_xlabel(r'First/Last Hit $\Delta$t / Channel / Event [$\mu$s]')
    ax4.set_ylabel(r'Channel Count / 0.5 $\mu$s')
    ax4.set_yscale('log')
    ax4.set_title("Difference in Time between First and Last Hit\nPer Channel in Selected Events "+mc_title)
    ax4.legend()
    plt.savefig(sample_type+"_selected_events_first_last_hit_deltat_per_channel_per_event.png")
    plt.close(fig4)

    return