import fitz
import glob
import os
import sys
import pdb
import shutil
import subprocess
import psutil

def isChromeOpen():
    chromeOpen = False
    for process in psutil.process_iter(['name', 'cmdline']):
        try:
            if process.info['name'] and 'chrome' in process.info['name'].lower():
                if process.info['cmdline'] and '--kiosk-printing' in process.info['cmdline']:
                    return False
                else:
                    chromeOpen = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return chromeOpen


def optimizePDF(pathPDF):

    doc = fitz.open('shuffled_' + pathPDF)
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        page.clean_contents()

    while len(doc.embfile_names()) > 0:
        doc.embfile_del(doc.embfile_names()[-1])

    doc.save('shuffled_temp_' + pathPDF, garbage=4, deflate=True, clean=True)
    doc.close()

    os.remove("shuffled_" + pathPDF)

def distSum(a, maxDist):
    totalDist = 0
    gDist = 0
    for i in range(len(a)):
        k = i + 1
        while k < len(a):
            if a[k] == a[i]:
                if k - i > maxDist and (a[i][4:6].lower() == 'nf' or a[i][0:3].lower() != 'wob'):
                    return 'errDist', ''
                if k - i > gDist and (a[i][4:6].lower() == 'nf' or a[i][0:3].lower() != 'wob'):
                    gDist = k - i
                if k - i == 1:
                    tempCount = 1
                    while tempCount + k < len(a):
                        if a[tempCount + k] != a[i]:
                            break
                        tempCount += 1
                    tempCount = tempCount - 1
                    totalDist += -10000 * ((tempCount + k) - i)
                elif k - i == 2:
                    totalDist += 100
                elif k - i == 3:
                    totalDist += 102
                else:
                    totalDist += 103   # if this value is changed it must also be changed at end of program for score denominator
                break
            else:
                k += 1
    return totalDist, gDist

def qualityTest(a):
    msg = "\nWARNING: this deck may have poor shuffle starting at page "
    msgEnd = " consider using different PKs"
    for i in range(len(a)):
        if i + 2 < len(a) and a[i] == a[i+1] == a[i+2]:
            return msg + str(i+1) + msgEnd
        elif i + 10 < len(a) and a[i] == a[i+2] == a[i+4] == a[i+6] == a[i+8] == a[i+10]:
            return msg + str(i+1) + msgEnd
    return ""


pdf_files = glob.glob("*.pdf")

if not os.path.exists('oldFiles'):
    os.mkdir('oldFiles')

for pdf in pdf_files:
    if 'shuffled' in pdf.lower() or 'progresscheck' in pdf.lower():
        target = os.path.join('oldFiles', os.path.basename(pdf))
        shutil.move(pdf, target)

pdf_files = glob.glob("*.pdf")

messages = []

printBool = input("\nDo you want to print pdfs? (y/n): ")
while isinstance(printBool, str):
    if printBool.lower() == 'n':
        printBool = False
    elif printBool.lower() == 'y':
        printBool = True
        m = ''
        while isChromeOpen() and m.lower() != 'b':
            m = input("\nSome instances of chrome are running, please close all instances before proceeding, or enter b to bypass: ")
        print("\n\n\n")
    else:
        printBool = input("\nInvalid Input. Do you want to print pdfs? (y/n): ")


pdfIndex = 0

while pdfIndex < len(pdf_files):
    pdf_path = pdf_files[pdfIndex]
    print(f"\nReading: {pdf_path}")

    doc = fitz.open(pdf_path)
    text = ""
    pkCount = {}
    arrayPKs = []
    hasWOB = False
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()

        offset1 = 3
        offset2 = 7
        index = text.lower().find("pk_")
        if index == -1:
            index = text.lower().find("pk-")
        if index == -1:
            index = text.lower().find("wob_")
            offset1 = 0
            offset2 = 7
        if index == -1:
            index = text.lower().find("wob-")
        if index == -1:
            print("\nERROR: No pks found")
            doc.close()
            input("Press Enter to exit...")
            sys.exit()

        pkNum = text[index + offset1 : index + offset2]

        if offset1 == 0 and pkNum[0:3].lower() != "wob":
            print("\nERROR: WOB value of " + pkNum + " found")
            doc.close()
            input("Press Enter to exit...")
            sys.exit()

        if offset1 == 3 and not pkNum.isdigit() and pkNum[0:2].lower() != "nf":
            print("\nERROR: pk value of " + pkNum + " found")
            doc.close()
            input("Press Enter to exit...")
            sys.exit()

        if offset1 == 0 and pkNum[4:6].lower() != "nf":
            hasWOB = True

        arrayPKs.append(pkNum)
        if pkNum in pkCount:
            pkCount[pkNum][0] += 1
            pkCount[pkNum][1].append(page_num)
        else:
            pkCount[pkNum] = []
            pkCount[pkNum].append(1)
            pkCount[pkNum].append([page_num])


    
    improving = True

    maxDist = 9
    lastWOBPage = ''
    arraySize = len(arrayPKs)

    if hasWOB:
        for r in range(len(arrayPKs)):
            if arrayPKs[r][0:3].lower() == 'wob' and arrayPKs[r][4:6].lower() != 'nf':
                lastWOBPage = arrayPKs.pop(r)
                arrayPKs.append(lastWOBPage)
                arraySize = arraySize - 1
                break
        if lastWOBPage == '':
            print('\nERROR: Expecting pdf to have WOB but none found')
            doc.close()
            input("Press Enter to exit...")
            sys.exit()



    bestDist, globalDist = distSum(arrayPKs, maxDist)


    if bestDist == 'errDist':
        print("\nError: initial deck exceeded maxPK distance")
        doc.close()
        input("Press Enter to exit...")
        sys.exit()


    print('')
    print(arrayPKs)


    while improving:
        improving = False
        for i in range(arraySize):
            k = i + 1
            while k < arraySize:
                p = arrayPKs.pop(k)
                arrayPKs.insert(i + 1, p)
                if 'wob' in arrayPKs[0].lower() and 'nf' not in arrayPKs[0].lower():
                    p = arrayPKs.pop(i + 1)
                    arrayPKs.insert(k, p)
                    k += 1
                    continue
                tempDist, tempGlobalDist = distSum(arrayPKs, maxDist)
                if tempDist == 'errDist':
                    p = arrayPKs.pop(i + 1)
                    arrayPKs.insert(k, p)
                elif tempDist > bestDist:
                    bestDist = tempDist
                    improving = True
                    globalDist = tempGlobalDist
                else:
                    p = arrayPKs.pop(i + 1)
                    arrayPKs.insert(k, p)
                k += 1
            k = i - 1
            while k >= 0:
                p = arrayPKs.pop(k)
                arrayPKs.insert(i, p)
                if 'wob' in arrayPKs[0].lower() and 'nf' not in arrayPKs[0].lower():
                    p = arrayPKs.pop(i)
                    arrayPKs.insert(k, p)
                    k = k - 1
                    continue
                tempDist, tempGlobalDist = distSum(arrayPKs, maxDist)
                if tempDist == 'errDist':
                    p = arrayPKs.pop(i)
                    arrayPKs.insert(k, p)
                elif tempDist > bestDist:
                    bestDist = tempDist
                    improving = True
                    globalDist = tempGlobalDist
                else:
                    p = arrayPKs.pop(i)
                    arrayPKs.insert(k, p)
                k = k - 1

    print('')
    print(arrayPKs)

    msg = qualityTest(arrayPKs)
    if msg != '':
        print(msg)
        messages.append(pdf_files[pdfIndex])

    totalPossibleScore = 0
    for k in pkCount.keys():
        totalPossibleScore += (pkCount[k][0] - 1) * 103

    print(f'\nDeck Shuffle Score (negative is bad, higher score is better): {bestDist:,} / {totalPossibleScore:,}')

    print(f'\nMax Distance Between Topics: {globalDist}')



    newPDF = fitz.open()
    for pk in arrayPKs:
        page = pkCount[pk][1].pop(0)
        newPDF.insert_pdf(doc, from_page=page, to_page=page)

    doc.close()

    target = os.path.join('oldFiles', os.path.basename(pdf_files[pdfIndex]))
    shutil.move(pdf_files[pdfIndex], target)


    newPDF.save('shuffled_' + pdf_files[pdfIndex])
    newPDF.close()


    if printBool:
        if msg != '':
            response = input("\nThis pdf had poor shuffle. Do you still want to print this pdf? (y/n): ")
            response = response.lower()
            while response != 'y' and response != 'n':
                print("\nInvalid Input\n")
                response = input("\nThis pdf had poor shuffle. Do you still want to print this pdf? (y/n): ")
                response = response.lower()
            if response == 'y':
                optimizePDF(pdf_files[pdfIndex])
                printerName = "HP42921F (HP LaserJet Pro 4001)"
                tempPath = 'shuffled_temp_' + pdf_files[pdfIndex]

                chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
                tempPath = os.path.abspath(tempPath).replace("\\", "/")
                tempPath = f"file:///" + tempPath
                
                subprocess.run([
                    chrome_path,
                    "--print-to-pdf-no-header",
                    f"--print-to-printer={printerName}",
                    "--kiosk-printing",
                    tempPath
                ])

                if pdfIndex != len(pdf_files) - 1:
                    input("\n\nPress Enter to Continue...")
        else:
            optimizePDF(pdf_files[pdfIndex])
            printerName = "HP42921F (HP LaserJet Pro 4001)"
            tempPath = 'shuffled_temp_' + pdf_files[pdfIndex]

            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
            tempPath = os.path.abspath(tempPath).replace("\\", "/")
            tempPath = f"file:///" + tempPath
            
            subprocess.run([
                chrome_path,
                "--print-to-pdf-no-header",
                f"--print-to-printer={printerName}",
                "--kiosk-printing",
                tempPath
            ])

            if pdfIndex != len(pdf_files) - 1:
                input("\n\nPress Enter to Continue...")


    while pdfIndex == len(pdf_files) - 1:
        tempResponse = input("\n\nTo continue, add more decks to directory then press enter to continue or enter q to quit...")
        if tempResponse.lower() == 'q':
            break

        pdf_files = glob.glob("*.pdf")

        if not os.path.exists('oldFiles'):
            os.mkdir('oldFiles')

        t = 0
        while t < len(pdf_files):

            if 'progresscheck' in pdf_files[t].lower():
                target = os.path.join('oldFiles', os.path.basename(pdf_files[t]))
                shutil.move(pdf_files[t], target)
                del pdf_files[t]
            elif 'shuffled' in pdf_files[t].lower():
                del pdf_files[t]
            else:
                t += 1

        pdfIndex = -1


    print('\n\n\n')
    pdfIndex += 1


if len(messages) != 0:
    print('\nWarnings:')
for m in messages:
    print('\n' + m)

print("\n\n\nSuccess")

input("\n\nPress Enter to exit...")

print("")
