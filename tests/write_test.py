import sys
import os
import time
import threading
sys.path.append(os.path.abspath("./"))
import numpy as np
from logic.loglib import LogManagerWrapper,LogLevels

#this script generates random entries every few milliseconds using several threads and is intended to test the updating functions and multithreading access to the same file.

sample_text = """ Returning to the Spouter-Inn from the Chapel, I found Queequeg there quite alone; he having left the Chapel before the benediction some time. He was sitting on a bench before the fire,
 with his feet on the stove hearth, and in one hand was holding close up to his face that little negro idol of his; peering hard into its face, and with a jack-knife gently whittling away at its nose,
meanwhile humming to himself in his heathenish way. But being now interrupted, he put up the image; and pretty soon, going to the table, took up a large book there, and placing it on his lap
began counting the pages with deliberate regularity; at every fiftieth page—as I fancied—stopping a moment, looking vacantly around him, and giving utterance to a long-drawn gurgling whistle 
of astonishment. He would then begin again at the next fifty; seeming to commence at number one each time, as though he could not count more than fifty, and it was only by such a large number 
of fifties being found together, that his astonishment at the multitude of pages was excited. With much interest I sat watching him. Savage though he was, and hideously marred
about the face—at least to my taste—his countenance yet had a something in it which was by no means disagreeable. You cannot hide the soul. Through all his unearthly tattooings,
I thought I saw the traces of a simple honest heart; and in his large, deep eyes, fiery black and bold, there seemed tokens of a spirit that would dare a thousand devils.
And besides all this, there was a certain lofty bearing about the Pagan, which even his uncouthness could not altogether maim. He looked like a man who had never cringed
and never had had a creditor. Whether it was, too, that his head being shaved, his forehead was drawn out in freer and brighter relief, and looked more expansive than it otherwise would,
this I will not venture to decide; but certain it was his head was phrenologically an excellent one. It may seem ridiculous, but it reminded me of General Washington’s head, as seen in
the popular busts of him. It had the same long regularly graded retreating slope from above the brows, which were likewise very projecting, like two long promontories thickly wooded on top.
Queequeg was George Washington cannibalistically developed. Whilst I was thus closely scanning him, half-pretending meanwhile to be looking out at the storm from the casement,
he never heeded my presence, never troubled himself with so much as a single glance; but appeared wholly occupied with counting the pages of the marvellous book. 
Considering how sociably we had been sleeping together the night previous, and especially considering the affectionate arm I had found thrown over me upon waking in the morning,
I thought this indifference of his very strange. But savages are strange beings; at times you do not know exactly how to take them. At first they are overawing; their calm
self-collectedness of simplicity seems a Socratic wisdom. I had noticed also that Queequeg never consorted at all, or but very little, with the other seamen in the inn.
 He made no advances whatever; appeared to have no desire to enlarge the circle of his acquaintances. All this struck me as mighty singular; yet, upon second thoughts,
there was something almost sublime in it. Here was a man some twenty thousand miles from home, by the way of Cape Horn, that is—which was the only way he could get there—thrown 
among people as strange to him as though he were in the planet Jupiter; and yet he seemed entirely at his ease; preserving the utmost serenity; content with his own companionship;
always equal to himself. Surely this was a touch of fine philosophy; though no doubt he had never heard there was such a thing as that. But, perhaps, to be true philosophers,
we mortals should not be conscious of so living or so striving. So soon as I hear that such or such a man gives himself out for a philosopher, I conclude that, like the dyspeptic old woman,
he must have “broken his digester.” """.split()

pid = os.getpid()
n_thread = 0

def write_thread_func(fpath,lock) :

    global n_thread
    Lm = LogManagerWrapper(fpath)
    n_thread += 1
    topic = fpath.split("/")[-1]

    for i in range(30) :
        time.sleep(np.random.randint(1000, 3000) / 1000)
        message = ' '.join(np.random.choice(sample_text,np.random.randint(10,15)))
        d6 = np.random.randint(1,7)
        lock.acquire()
        try :
            if d6>=5 :
                Lm.new_entry(message, np.random.randint(0, 5), topic,{"mat4": np.random.randn(np.random.randint(2,4),np.random.randint(1,4))})
            else :
                Lm.new_entry(message,np.random.randint(0,5),topic)
        finally :
            lock.release()


lock = threading.Lock()
threadlist = []
for j in range(100) :
    threadlist += [threading.Thread(target = write_thread_func,args=[os.path.abspath("./tests/moby/moby{}.yaml").format(j),lock]) for i in range(4)]
np.random.shuffle(threadlist)
for thread in threadlist:
    thread.start()
