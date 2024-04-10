const fs = require('fs');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

rl.question('Enter the path to the JSON file to split: ', (filePath) => {
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            console.error('Error reading file:', err);
            rl.close();
            return;
        }

        let jsonData;
        try {
            jsonData = JSON.parse(data);
        } catch (parseError) {
            console.error('Error parsing JSON:', parseError);
            rl.close();
            return;
        }

        rl.question('Enter the number of parts to split the file into: ', (numPartsStr) => {
            const numParts = parseInt(numPartsStr, 10);
            if (isNaN(numParts) || numParts <= 0) {
                console.error('Invalid number of parts. Please enter a positive integer.');
                rl.close();
                return;
            }

            const totalItems = jsonData.length;
            const itemsPerPart = Math.floor(totalItems / numParts);
            const remainder = totalItems % numParts;

            let startIndex = 0;
            for (let i = 0; i < numParts; i++) {
                const partSize = itemsPerPart + (i < remainder ? 1 : 0);
                const partData = jsonData.slice(startIndex, startIndex + partSize);
                const partFilename = `${filePath}_part${i + 1}.json`;

                fs.writeFile(partFilename, JSON.stringify(partData, null, 2), (writeErr) => {
                    if (writeErr) {
                        console.error(`Error writing part ${i + 1} to file:`, writeErr);
                    } else {
                        console.log(`Part ${i + 1} written to ${partFilename}`);
                    }
                });

                startIndex += partSize;
            }

            rl.close();
        });
    });
});
