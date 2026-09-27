const express = require('express');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const bodyParser = require('body-parser');

// Ensure current user's Python 3.13 is prioritized in PATH on Windows
if (process.platform === 'win32') {
    const userPython = path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python313');
    const userPythonScripts = path.join(userPython, 'Scripts');
    if (fs.existsSync(userPython)) {
        process.env.PATH = `${userPython}${path.delimiter}${userPythonScripts}${path.delimiter}${process.env.PATH}`;
    }
}

const app = express();
const PORT = 3001; // Running on a separate port

app.use(cors());
app.use(bodyParser.json({ limit: '500mb' }));
app.use(bodyParser.urlencoded({ limit: '500mb', extended: true }));

// Serve static files from current directory
// Serve static files from ROOT directory (parent of System)
app.use(express.static(path.join(__dirname, '..')));

// Import Backend Logic
require('../backend/api')(app);

// Default route - Show the Data Generate tool
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'createbulkdata.html'));
});

app.listen(PORT, () => {
    console.log(`\n==================================================`);
    console.log(`✅ Data Generate Server running on http://localhost:${PORT}`);
    console.log(`📂 SERVING FROM: ${__dirname}`);
    console.log(`==================================================\n`);
});
